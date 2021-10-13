FROM python:3.9-slim-buster

RUN apt -y update
RUN apt -y install make
RUN apt -y install chromium-driver
RUN apt -y install openjdk-11-jre
RUN apt -y install wget
RUN apt -y install xauth

RUN useradd --create-home --shell /bin/bash localtester

COPY entrypoint.sh /entrypoint.sh
COPY . /home/localtester/change-analyzer
RUN chown -R localtester:localtester /home/localtester/change-analyzer

# EXPOSE 9515/tcp
# EXPOSE 4444/tcp

USER localtester
WORKDIR /home/localtester
RUN wget https://github.com/SeleniumHQ/selenium/releases/download/selenium-3.141.59/selenium-server-standalone-3.141.59.jar
RUN cd /home/localtester/change-analyzer && make install

ENTRYPOINT ["/entrypoint.sh"]
