import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, DIRECTORY / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


evidence = module('evidence', 'evidence.py')
fetch = module('fetch_source', 'fetch-source.py')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        # Retain test artifacts, including failed assertions, for investigation.
        self.root = Path(tempfile.mkdtemp(prefix='relay-ci-tests-'))
        self.release = json.loads((DIRECTORY / 'release.json').read_text())
        self.description = {'Measurements': self.release['pcrs']}
        self.env = {
            'GITHUB_SHA': 'b' * 40, 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_REPOSITORY': 'example/relay', 'RUNNER_ENVIRONMENT': 'github-hosted',
            'GITHUB_WORKFLOW_REF': 'example/relay/.github/workflows/reproduce-enclave.yml@refs/heads/main',
        }
        self.inputs = self.root / 'inputs'
        for index in (1, 2):
            directory = self.inputs / f'build-{index}'
            directory.mkdir(parents=True)
            # These are explicit synthetic test bytes, never deployment evidence.
            (directory / 'attested-relay.eif').write_bytes(f'synthetic EIF {index}'.encode())
            evidence.write(directory / 'description.json', self.description)
            evidence.write(directory / 'build-pcrs.json', self.description)
            evidence.write(directory / 'docker-inspect.json', [{'Id': self.release['docker_image_id']}])
            with patch.dict(os.environ, self.env):
                evidence.build(directory, index, self.release)

    def compare(self, description=None):
        description = self.description if description is None else description
        with patch.dict(os.environ, self.env), patch.object(
            evidence.subprocess, 'check_output', return_value=json.dumps(description)
        ) as describe:
            evidence.compare(self.inputs, self.root / 'verified', self.release)
            return describe.call_count

    def change_record(self, key, value):
        path = self.inputs / 'build-1/build.json'
        record = json.loads(path.read_text())
        record[key] = value
        path.write_text(json.dumps(record))

    def test_metadata_difference_is_allowed_but_measurements_recomputed(self):
        self.assertEqual(self.compare(), 2)
        report = json.loads((self.root / 'verified/reproduction.json').read_text())
        self.assertFalse(report['full_eif_bytes_equal'])

    def test_wrong_source_rejected(self):
        self.change_record('source_sha256', '0' * 64)
        with self.assertRaisesRegex(ValueError, 'source_sha256'):
            self.compare()

    def test_other_run_rejected(self):
        self.change_record('run_id', '999')
        with self.assertRaisesRegex(ValueError, 'run_id'):
            self.compare()

    def test_tampered_eif_rejected(self):
        (self.inputs / 'build-1/attested-relay.eif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.compare()

    def test_forged_build_measurements_do_not_bypass_remeasurement(self):
        bad = copy.deepcopy(self.description)
        bad['Measurements']['PCR0'] = '0' * 96
        with self.assertRaisesRegex(ValueError, 'built PCRs differ'):
            self.compare(bad)

    def test_self_hosted_claim_rejected(self):
        self.change_record('runner_environment', 'self-hosted')
        with self.assertRaisesRegex(ValueError, 'runner_environment'):
            self.compare()

    def test_wrong_archive_hash_rejected_before_extract(self):
        destination = self.root / 'source'
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            fetch.extract(b'wrong archive', destination, self.release)
        self.assertFalse(destination.exists())

    def test_archive_traversal_rejected(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            member = tarfile.TarInfo('attested-relay-' + self.release['source_commit'] + '/../escape')
            archive.addfile(member, io.BytesIO(b''))
        payload = data.getvalue()
        release = dict(self.release, source_sha256=evidence.hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError, 'noncanonical'):
            fetch.extract(payload, self.root / 'source', release)
        self.assertFalse((self.root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
