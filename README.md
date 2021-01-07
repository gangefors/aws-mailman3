# Mailman3 in AWS using Mailgun to send mail

## On localhost

### Create SSK key pair

    ssh-keygen  -t rsa -f ~/.ssh/mykey_rsa


## In AWS Management Console 

### Import SSH keys

### Launch EC2 instance

1. Choose AMI

   Ubuntu Server 20.04 LTS (HVM), SSD Volume Type - ami-0a3a4169ad7cb0d77

2. Choose Instance Type

   micro for Mailman3 Core + Postorius (Free tier eligible)

   small for Mailman3 Core + Postorius + Hyperkitty

3. Configure Instance

   Update any setting as needed, defaults work fine

4. Add Storage (8GB works fine)

5. Add Tags (optional)

6. Configure Security Group

   | Type       | Port | Destination | Description
   |------------|-----:|-------------|------------
   | SSH        | 22   | My IP       |
   | Custom TCP | 8024 | Anywhere    | LMTP
   | HTTP       | 80   | Anywhere    |
   | HTTPS      | 443  | Anywhere    |

7. Review

   Launch and select imported key pair

### Allocate Elastic IP

Use defaults and add Tags if you want, click Allocate.
Select the new Elastic IP address and Associate to your instance.


## In Mailgun management interface

### Sending > Domains > Add new domain

Enter your domain where you want Mailman to be accessible.

Save the instructions on how to update your DNS records.


## At your DNS provider

### Add DNS records

Follow the Mailgun instructions regarding updating DNS records at your domain provider.

Also add an A record with the Elastic IP we allocated to our EC2 instance.

It will take some time for the DNS to become updated. Mailgun will send an email when all is ready.


## On EC2 host

### Connect to the EC2 instance

    ssh -i ~/.ssh/mykey_rsa ubuntu@<Elastic IP or DNS>

### Install Docker and other dependencies

    curl -fsSL https://get.docker.com | sudo sh
    sudo apt install --no-install-recommends -y docker-compose nginx pwgen

### Prepare directories and download files

    # Create directories and download docker-compose file
    sudo mkdir -p /opt/mailman/core /opt/mailman/database /opt/mailman/web
    mkdir -p ~/mailman3
    cd ~/mailman3
    wget https://raw.githubusercontent.com/gangefors/aws-mailman3/master/.env
    wget https://raw.githubusercontent.com/gangefors/aws-mailman3/master/docker-compose.yaml

### Update configuration

Open `.env` file and update configuration.

### Configure nginx webserver

    sudo vim /etc/nginx/sites-available/default

Replace the matching content with the following.

    server_name <your_domain>;

    location / {
        proxy_pass http://172.19.199.3:8000;
        include uwsgi_params;
        uwsgi_read_timeout 300;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    location /static/ {
        root /opt/mailman/web/;
    }


### Add HTTPS certificates

    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot

Answer the questions when running this following command.

    sudo certbot --nginx


### Configure MTA

> TODO: Without this no emails can be sent to the lists.


### Start Mailman containers

    docker-compose up -d


## References

https://asynchronous.in/docker-mailman/
https://xiaoxing.us/2018/01/01/deploy-mailman-3-on-aws-using-docker/
http://bachmeb.weebly.com/gnu-mailman-on-ec2.html
https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script
https://certbot.eff.org/
