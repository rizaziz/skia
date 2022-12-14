#!/usr/bin/env python2.7
#
# Copyright 2017 Google Inc.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import glob
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile

# Arguments to the script:
#  pkg              path to application directory, e.g. out/Debug/dm.app
#                   executable and plist should already be in this directory
#  identstr         search string (regex fragment) for code signing identity
#  profile          path or name of provisioning profile
pkg,identstr,profile = sys.argv[1:]

# Find the signing identity.
identity = None
for line in subprocess.check_output([
    'security', 'find-identity']).decode('utf-8').split('\n'):
  m = re.match(r'''.*\) (.*) "''' + identstr + '"', line)
  if m:
    identity = m.group(1)
if identity is None:
  print("Signing identity matching '" + identstr + "' not found.")
  print("Please verify by running 'security find-identity' or checking your keychain.")
  sys.exit(1)

# Find the mobile provisioning profile.
mobileprovision = None
if os.path.isfile(profile):
  mobileprovision = profile
else:
  for p in glob.glob(os.path.join(os.environ['HOME'], 'Library', 'MobileDevice',
                                  'Provisioning Profiles',
                                  '*.mobileprovision')):
    if re.search(r'''<key>Name</key>
\t<string>''' + profile + r'''</string>''', open(p, 'rb').read().decode("utf-8", "ignore"), re.MULTILINE):
      mobileprovision = p
if mobileprovision is None:
  print("Provisioning profile matching '" + profile + "' not found.")
  print("Please verify that the correct profile is installed in '${HOME}/Library/MobileDevice/Provisioning Profiles' or specify the path directly.")
  sys.exit(1)

# The .mobileprovision just gets copied into the package.
shutil.copy(mobileprovision,
            os.path.join(pkg, 'embedded.mobileprovision'))

# Extract the appliciation identitifer prefix from the .mobileprovision.
m = re.search(r'''<key>ApplicationIdentifierPrefix</key>
\t<array>
\t<string>(.*)</string>''', open(mobileprovision, 'rb').read().decode("utf-8", "ignore"), re.MULTILINE)
prefix = m.group(1)

app, _ = os.path.splitext(os.path.basename(pkg))

# Write a minimal entitlements file, then codesign.
with tempfile.NamedTemporaryFile() as f:
  f.write('''
<plist version="1.0">
  <dict>
    <key>application-identifier</key> <string>{prefix}.com.google.{app}</string>
    <key>get-task-allow</key>         <true/>
  </dict>
</plist>
'''.format(prefix=prefix, app=app).encode("utf-8"))
  f.flush()

  subprocess.check_call(['codesign',
                         '--force',
                         '--sign', identity,
                         '--entitlements', f.name,
                         '--timestamp=none',
                         pkg])
