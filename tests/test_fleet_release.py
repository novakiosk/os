import base64
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
helper=importlib.machinery.SourceFileLoader('update_helper',str(ROOT/'files/system/usr/libexec/novakiosk-system-update')).load_module()
DIGEST='sha256:'+'a'*64
COMMAND='e52a453f-2ec8-44ef-bf92-cc633de41c6e'

def deployment(digest=DIGEST,booted=False):
    return {'booted':booted,'container-image-reference-digest':digest,
            'container-image-reference':'ostree-image-signed:docker://ghcr.io/novakiosk/os@'+digest}


class RequestTests(unittest.TestCase):
    def test_unit_preserves_backend_instance(self):
        unit=(ROOT/'files/system/usr/lib/systemd/system/novakiosk-system-update@.service').read_text()
        command=next(line.removeprefix('ExecStart=') for line in unit.splitlines() if line.startswith('ExecStart='))
        instance='rpm-ostree'
        unescaped=subprocess.check_output(['systemd-escape','--unescape',instance],text=True).strip()
        self.assertEqual(unescaped,'rpm/ostree')
        argv=command.replace('%i',instance).replace('%I',unescaped).split()
        self.assertEqual(argv,['/usr/libexec/novakiosk-system-update','rpm-ostree'])
        # Stop at the non-OSTree guard: the real parser must accept the unit's argument.
        with patch.object(helper.sys,'argv',argv),patch.object(helper.os,'geteuid',return_value=0),patch.object(helper.os.path,'isfile',return_value=False):
            self.assertEqual(helper.main(),69)

    def request(self, value):
        with patch.object(helper,'protected_read',return_value=json.dumps(value).encode()):
            return helper.read_request(123)

    def test_exact_request_and_rejections(self):
        valid={'version':1,'commandId':COMMAND,'imageDigest':DIGEST,'action':'rollback'}
        self.assertEqual(self.request(valid),(DIGEST,"rollback"))
        for key,value in [('version',True),('commandId',COMMAND.upper()),('commandId','../foo'),
                          ('imageDigest',DIGEST+';reboot'),('imageDigest','latest'),('action','upgrade'),('action',{}),('repository','evil')]:
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,TypeError)):
                self.request(dict(valid,**{key:value}))
        for raw in [b'{}',b'\xff',b'{"version":1,"version":1}']:
            with patch.object(helper,'protected_read',return_value=raw),self.assertRaises(ValueError):
                helper.read_request(123)

    def test_fixed_request_file_bounds_and_ownership(self):
        with patch.object(helper,'protected_read',return_value=b'{}') as reader,self.assertRaises(ValueError):
            helper.read_request(123)
        reader.assert_called_once_with('/var/lib/novakiosk-agentd-helpers/kiosk/system-update.json',123,4096,private=True)

    def test_real_secure_file_walk_rejects_symlinks_modes_hardlinks_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'parent').mkdir(mode=0o700)
            file=root/'parent/request'
            file.write_bytes(b'valid');file.chmod(0o600)
            real_open=os.open
            def rooted(path,*args,**kwargs):
                return real_open(root if path=='/' else path,*args,**kwargs)
            with patch.object(helper.os,'open',side_effect=rooted):
                read=lambda:helper.protected_read('/parent/request',os.getuid(),16,True)
                self.assertEqual(read(),b'valid')
                file.chmod(0o644)
                with self.assertRaises(ValueError):read()
                file.chmod(0o600);file.write_bytes(b'x'*17)
                with self.assertRaises(ValueError):read()
                file.write_bytes(b'valid');os.link(file,root/'hardlink')
                with self.assertRaises(ValueError):read()
                (root/'hardlink').unlink();file.unlink();file.symlink_to(root/'target')
                (root/'target').write_bytes(b'valid')
                with self.assertRaises(OSError):read()
                file.unlink();file.write_bytes(b'valid');file.chmod(0o600)
                (root/'parent').rename(root/'original');(root/'parent').symlink_to(root/'original',target_is_directory=True)
                with self.assertRaises(OSError):read()

    def test_wrong_owner_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'request';file.write_bytes(b'x');file.chmod(0o600)
            real_open=os.open
            def rooted(path,*args,**kwargs):return real_open(directory if path=='/' else path,*args,**kwargs)
            with patch.object(helper.os,'open',side_effect=rooted),self.assertRaises(ValueError):
                helper.protected_read('/request',os.getuid()+1,16,True)

    def test_backend_rejected_without_command(self):
        for args in [[],['upgrade'],['rpm-ostree','extra']]:
            with patch.object(helper.sys,'argv',['helper']+args),patch.object(helper.subprocess,'run') as run:
                self.assertEqual(helper.main(),64)
                run.assert_not_called()


class StageTests(unittest.TestCase):
    def test_exact_signed_rebase_and_verify(self):
        boot=deployment('sha256:'+'b'*64,True)
        with patch.object(helper,'status',side_effect=[[boot],[deployment(),boot]]),patch.object(helper.subprocess,'run') as run:
            helper.stage(DIGEST,"rollback")
            self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','rebase','ostree-image-signed:docker://ghcr.io/novakiosk/os@'+DIGEST])
            self.assertEqual(run.call_args.kwargs['timeout'],1740)
            self.assertNotIn('stderr',run.call_args.kwargs)

    def test_pending_conflicts_and_insecure_reference(self):
        boot=deployment('sha256:'+'b'*64,True)
        for pending in [deployment('sha256:'+'c'*64),dict(deployment(),**{'container-image-reference':'ostree-unverified-registry:ghcr.io/novakiosk/os@'+DIGEST})]:
            with patch.object(helper,'status',return_value=[pending,boot]),patch.object(helper.subprocess,'run') as run,self.assertRaises(ValueError):
                helper.stage(DIGEST,"rollback")
            run.assert_not_called()

    def test_existing_target_is_idempotent(self):
        for current in [[deployment(booted=True)],[deployment(),deployment('sha256:'+'b'*64,True)]]:
            with patch.object(helper,'status',return_value=current),patch.object(helper.subprocess,'run') as run:
                helper.stage(DIGEST,"rollback")
            run.assert_not_called()

    def test_false_success_rejected(self):
        with patch.object(helper,'status',return_value=[deployment('sha256:'+'b'*64,True)]),patch.object(helper.subprocess,'run'),self.assertRaises(ValueError):
            helper.stage(DIGEST,"rollback")

    def test_trust_policy_cannot_be_relaxed(self):
        files={helper.KEY:(ROOT/'cosign.pub').read_bytes(),'/etc/containers/policy.json':(ROOT/'files/system/etc/containers/policy.json').read_bytes(),
               '/etc/containers/registries.d/novakiosk.yaml':(ROOT/'files/system/etc/containers/registries.d/novakiosk.yaml').read_bytes()}
        with patch.object(helper,'protected_read',side_effect=lambda path,*args:files[path]):
            helper.verify_policy()
            files['/etc/containers/policy.json']=b'{"default":[{"type":"insecureAcceptAnything"}]}'
            with self.assertRaises(ValueError):helper.verify_policy()



class AutomaticTests(unittest.TestCase):
    def test_only_unoccupied_signed_latest_origin_updates(self):
        latest=dict(deployment(booted=True), **{'container-image-reference':'ostree-image-signed:docker://ghcr.io/novakiosk/os:latest'})
        for state, expected in [([latest],True),([deployment(),latest],False),([deployment(booted=True)],False),([dict(latest,**{'container-image-reference':'ostree-unverified-registry:ghcr.io/evil/os:latest'})],False)]:
            with self.subTest(state=state),patch.object(helper,'status',return_value=state),patch.object(helper.subprocess,'run') as run:
                helper.automatic()
                self.assertEqual(run.called,expected)
                if expected:self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','upgrade','--quiet','--trigger-automatic-update-policy'])
        with patch.object(helper,'status',side_effect=helper.TransactionPending()),patch.object(helper.subprocess,'run') as run:
            helper.automatic()
            run.assert_not_called()

    def test_mode_changes_and_pending_mode_conflict(self):
        held=deployment(booted=True)
        latest=dict(deployment(),**{'container-image-reference':'ostree-image-signed:docker://ghcr.io/novakiosk/os:latest'})
        for action in ['update','resume']:
            with patch.object(helper,'status',side_effect=[[held],[latest,held]]),patch.object(helper.subprocess,'run') as run:
                helper.stage(DIGEST,action)
                self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','rebase','ostree-image-signed:docker://ghcr.io/novakiosk/os:latest',DIGEST])
            with patch.object(helper,'status',return_value=[deployment(),held]),patch.object(helper.subprocess,'run') as run,self.assertRaises(ValueError):
                helper.stage(DIGEST,action)
            run.assert_not_called()

    def test_latest_origin_uses_deploy_for_new_digest_and_both_signed_aliases(self):
        for transport in ['docker://', 'registry:']:
            reference = 'ostree-image-signed:' + transport + helper.REPOSITORY + ':latest'
            boot = dict(deployment('sha256:'+'b'*64,True), **{'container-image-reference':reference})
            pending = dict(deployment(), **{'container-image-reference':reference})
            with self.subTest(transport=transport),patch.object(helper,'status',side_effect=[[boot],[pending,boot]]),patch.object(helper.subprocess,'run') as run:
                helper.stage(DIGEST,'update')
                self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','deploy',DIGEST])
            with patch.object(helper,'status',return_value=[dict(pending,booted=True)]),patch.object(helper.subprocess,'run') as run:
                helper.stage(DIGEST,'resume')
                run.assert_not_called()
            with patch.object(helper,'status',return_value=[boot]),patch.object(helper.subprocess,'run') as run:
                helper.automatic()
                self.assertTrue(run.called)
        for reference in ['ostree-unverified-registry:'+helper.REPOSITORY+':latest', 'ostree-image-signed:registry:'+helper.REPOSITORY+'-evil:latest']:
            self.assertIsNone(helper.signed_reference({'container-image-reference':reference}))

    def test_status_transaction_and_malformed_deployments(self):
        for value in [{'deployments':[deployment(booted=True)],'transaction':['upgrade']},
                      {'deployments':[]}, {'deployments':[None]}]:
            with patch.object(helper,'status_bytes',return_value=json.dumps(value).encode()),self.assertRaises(ValueError):
                helper.status()

    def test_rollback_changes_same_digest_automatic_origin(self):
        boot=dict(deployment(booted=True), **{'container-image-reference':'ostree-image-signed:docker://ghcr.io/novakiosk/os:latest'})
        with patch.object(helper,'status',side_effect=[[boot],[deployment(),boot]]),patch.object(helper.subprocess,'run') as run:
            helper.stage(DIGEST,'rollback')
            self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','rebase','ostree-image-signed:docker://ghcr.io/novakiosk/os@'+DIGEST])

    def test_shared_lock_excludes_manual_and_automatic_through_command(self):
        # Exercise real flock contention while replacing only root/boot/trust
        # checks and the backend. A second open must remain excluded throughout.
        with tempfile.TemporaryDirectory() as directory:
            lockpath=Path(directory)/'lock'
            real_open=os.open
            def opened(path,*args,**kwargs):
                return real_open(lockpath if path=='/run/novakiosk-system-update.lock' else path,*args,**kwargs)
            real_stat=os.fstat
            def owned(fd):
                values=list(real_stat(fd));values[4]=0
                return os.stat_result(values)
            def backend(*args, **kwargs):
                fd=real_open(lockpath,os.O_RDWR)
                try:
                    with self.assertRaises(BlockingIOError):helper.fcntl.flock(fd,helper.fcntl.LOCK_EX|helper.fcntl.LOCK_NB)
                finally:os.close(fd)
            for mode in ['automatic','rpm-ostree']:
                with patch.object(helper.sys,'argv',['helper',mode]),patch.object(helper.os,'geteuid',return_value=0),patch.object(helper.os.path,'isfile',return_value=True),patch.object(helper.os,'open',side_effect=opened),patch.object(helper.os,'fstat',side_effect=owned),patch.object(helper,'verify_policy'),patch.object(helper,'read_request',return_value=(DIGEST,'update')),patch.object(helper.pwd,'getpwnam'),patch.object(helper,'automatic',side_effect=backend),patch.object(helper,'stage',side_effect=backend):
                    self.assertEqual(helper.main(),0)
                    fd=real_open(lockpath,os.O_RDWR)
                    helper.fcntl.flock(fd,helper.fcntl.LOCK_EX|helper.fcntl.LOCK_NB)
                    try:self.assertEqual(helper.main(),0 if mode=='automatic' else 1)
                    finally:os.close(fd)


class CustomPolicyTests(unittest.TestCase):
    def test_custom_repository_stages_only_under_installed_policy(self):
        repository='ghcr.io/example/custom-os'
        files={helper.KEY:(ROOT/'cosign.pub').read_bytes(),
               '/etc/containers/policy.json':(ROOT/'files/system/etc/containers/policy.json').read_bytes().replace(b'ghcr.io/novakiosk/os',repository.encode()),
               '/etc/containers/registries.d/novakiosk.yaml':(ROOT/'files/system/etc/containers/registries.d/novakiosk.yaml').read_bytes().replace(b'ghcr.io/novakiosk/os',repository.encode())}
        with patch.object(helper,'protected_read',side_effect=lambda path,*args:files[path]):
            self.assertEqual(helper.verify_policy(),repository)
            files['/etc/containers/registries.d/novakiosk.yaml']=(ROOT/'files/system/etc/containers/registries.d/novakiosk.yaml').read_bytes()
            with self.assertRaises(ValueError):helper.verify_policy()
        boot=deployment('sha256:'+'b'*64,True)
        boot['container-image-reference']='ostree-image-signed:docker://'+repository+':latest'
        pending=deployment();pending['container-image-reference']='ostree-image-signed:docker://'+repository+'@'+DIGEST
        with patch.object(helper,'status',side_effect=[[boot],[pending,boot]]),patch.object(helper.subprocess,'run') as run:
            helper.stage(DIGEST,'rollback',repository)
            self.assertEqual(run.call_args.args[0],['/usr/bin/rpm-ostree','rebase','ostree-image-signed:docker://'+repository+'@'+DIGEST])
        self.assertIsNone(helper.signed_reference(pending))

if __name__=='__main__':unittest.main()
