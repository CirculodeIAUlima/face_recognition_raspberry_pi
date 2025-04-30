# Download Cmake (Windows)

- https://cmake.org/download/

# Download Firebase CLI (for Windows)

https://firebase.google.com/docs/cli#install-cli-windows
Download the Firebase CLI binary for Windows. (https://firebase.tools/bin/win/instant/latest)
Access the binary to open a shell where you can run the firebase command.
Continue to log in and test the CLI. (https://firebase.google.com/docs/cli#sign-in-test-cli)

# Create requirements.txt file
pip freeze > requirements.txt

# Install libraries from the requirements.txt file
pip install -r requirements.txt

# Files Execution Order

- image_capture_windows
- model_training_windows
- facial_recognition_hardware_windows
- facial_recognition_firebase

# Smtp test (gmass.co/smtp-test)

- smtp.gmail.com
- 465
- SSL
- Username = Gmail

# Check blobs

SELECT encode(blobdata::bytea, 'escape') FROM public.unknown_videos as o where mp4   != ''
SELECT id, encode(mp4::bytea, 'base64') as mp4 from unknown_videos where id=1;

# Set time zone in Postgres

SET TIME ZONE 'UTC';
