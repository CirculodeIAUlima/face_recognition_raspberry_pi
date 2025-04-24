# Miau
pip install face_recognition opencv-python numpy picamera2 imutils
pip install gpiozero 
pip install "numpy<2.2.0" --force-reinstall
pip install torch==2.5.1 torchvision==0.20.1 --force-reinstall
pip install torch torchvision
pip install psycopg2-binary face_recognition opencv-python numpy
pip install pyttsx3 schedule pandas
pip install apscheduler
pip install sqlalchemy
pip install dotenv

# Create requirements.txt file
pip freeze > requirements.txt

# Install libraries from the requirements.txt file
pip install -r requirements.txt

# Files Order

- image_capture_windows
- model_training_windows
- facial_recognition_windows
- facial_recognition_hardware_windows


# gmass.co/smtp-test

- smtp.gmail.com
- 465
- SSL
- Username = Gmail

# Set environment variables for SMTP

setx SMTP_USER      "tu-correo@gmail.com"
setx SMTP_PASSWORD  "tu_app_password_de_16_caracteres"
setx SMTP_HOST      = "smtp.gmail.com"   # opcional (por defecto es gmail)
setx SMTP_PORT      = "587"              # opcional

setx SMTP_USER      "ignaciodejesus.m.u@gmail.com"
setx SMTP_PASSWORD  "vqfe oiun jytg yokm"
echo $Env:SMTP_USER
echo $Env:SMTP_PASSWORD


# Check blobs
SELECT encode(blobdata::bytea, 'escape') FROM public.unknown_videos as o where mp4   != ''
SELECT id, encode(mp4::bytea, 'base64') as mp4 from unknown_videos where id=1;

# Set time zone in Postgres
SET TIME ZONE 'UTC';
