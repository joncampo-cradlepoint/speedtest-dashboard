FROM python:3.8

WORKDIR /usr/local/app/

COPY ./ /usr/local/app/

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "main.py"]