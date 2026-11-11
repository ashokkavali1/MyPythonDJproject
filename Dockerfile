FROM python:3
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install requirements.txt
COPY . .
CMD ['python','app.py']
