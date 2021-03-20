# Mailman3 in AWS

This guide will assist you in setting up Mailman3 in AWS.
We will be using Mailgun to send mail, but any provider will do.

When "your domain" is mentioned, it is in regards to the domain name where
you are running Mailman3, i.e. the doman name pointing to the EC2 instance.
For example `lists.example.com`.

## On localhost

### Create SSK key pair

    ssh-keygen  -t rsa -f ~/.ssh/mykey_rsa


## In AWS Management Console 

### Import SSH keys

Go to Network & Security > Key pairs and choose Actions > Import key pair.

Enter a name, browse for `~/.ssh/mykey_rsa.pub` and if you want you can add
tags to this item. Finalize by importing the key pair.

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

   | Type  | Port | Destination |
   |-------|-----:|-------------|
   | SSH   | 22   | My IP       |
   | SMTP  | 25   | Anywhere    |
   | HTTP  | 80   | Anywhere    |
   | HTTPS | 443  | Anywhere    |

7. Review

   Launch and select imported key pair

### Allocate Elastic IP

Use defaults and add Tags if you want, click Allocate.
Select the new Elastic IP address and Associate to your instance.


## In Mailgun management interface

### Sending > Domains > Add new domain

Enter the domain where you want Mailman3 to be accessible.

Save the instructions on how to update your DNS records.


## At your DNS provider

### Add DNS records

Add an A record with the Elastic IP we allocated to our EC2 instance. This
will be the domain name we you throughout this guide.

Also create an MX record that points to your EC2 domain name given
as the A record.

Follow the Mailgun instructions regarding updating the final DNS records.
Do NOT add Mailguns MX records, we don't want to recieve mail with Mailgun.

It will take some time for the DNS to update, but it will surely be ready
when we get to the point where we launch Mailman3.


## On EC2 host

Connect to the EC2 host.

    ssh -i ~/.ssh/mykey_rsa ubuntu@<Elastic IP or DNS>

### Dependencies

Docker, docker-compose and nginx is needed to run the service.

    curl -fsSL https://get.docker.com | sudo sh
    sudo DEBIAN_FRONTEND=noninteractive apt install -y docker-compose nginx postfix

### Preparations

Create directories and download docker-compose file.

    sudo mkdir -p /opt/mailman/core /opt/mailman/database /opt/mailman/web
    mkdir -p ~/mailman3
    cd ~/mailman3
    wget https://raw.githubusercontent.com/gangefors/aws-mailman3/master/.env
    wget https://raw.githubusercontent.com/gangefors/aws-mailman3/master/docker-compose.yaml

### Configure Mailman3

Open the `.env` file and update the variables.

### Configure nginx

    sudoedit /etc/nginx/sites-available/default

Replace the matching content with the following.

    server_name <your_domain>;

    location / {
        proxy_pass http://localhost:8000;
        include uwsgi_params;
        uwsgi_read_timeout 300;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    location /static/ {
        root /opt/mailman/web/;
    }


### Enable HTTPS

Add HTTPS certificates

    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot

Answer the questions when running this following command.

    sudo certbot --nginx


### Configure MTA

#### Configure Mailman3

Create `/opt/mailman/core/mailman-extra.cfg` with the following content.
Make sure to update `site_owner` with a valid email.

    [mta]
    incoming: mailman.mta.postfix.LMTP
    outgoing: mailman.mta.deliver.deliver
    lmtp_host: 127.0.0.1
    lmtp_port: 8024
    smtp_host: 172.19.199.1
    smtp_port: 25
    configuration: /etc/postfix-mailman.cfg

    [mailman]
    # This address is the "site owner" address.  Certain messages which must be
    # delivered to a human, but which can't be delivered to a list owner (e.g. a
    # bounce from a list owner), will be sent to this address.  It should point to
    # a human.
    site_owner: email@example.com

#### Configure Postfix

Create `/etc/postfix/sasl_passwd` and replace below with your credentials.

    smtp.eu.mailgun.org:587 postmaster@your_subdomain:mailgun_smtp_password

Set permissions and generate lookup table.

    sudo chmod 600 /etc/postfix/sasl_passwd
    sudo postmap /etc/postfix/sasl_passwd

Launch the Postfix configuration wizard.

    sudo dpkg-reconfigure postfix

Enter the following:

1. General type of mail configuration:

   Internet with smarthost

2. System mail name:

   The domain one you created a DNS A record for, e.g. `lists.example.com`.

3. SMTP relay host:

   Use the SMTP host from Mailgun's SMTP credentials, e.g. `smtp.eu.mailgun.org:587`.

4. Root and postmaster mail recipient: `<your@email.address>`

5. Other destinations to accept mail for:

   You can probably leave this as is, but make sure that your public domain
   is included, e.g. `lists.example.com`.

6. Force synchronous updates on mail queue: `No`

7. Local networks:

   Add `172.19.199.0/24` to allow for mail delivery to our Docker containers.

8. Mailbox size limit: `51200000`

   This is to make sure that disk space doesn't suddenly run out.

9. Local address extension character: `+`

10. Internet protocols to use: `all`

#### Additional Postfix configuration

Configure TSL certificates, make sure to replace `<domain name>`.

    sudo postconf -e smtpd_tls_cert_file=/etc/letsencrypt/live/<domain name>/fullchain.pem
    sudo postconf -e smtpd_tls_key_file=/etc/letsencrypt/live/<domain name>/privkey.pem

Finalize Postfix configuration

    sudo postconf -e smtp_sasl_auth_enable=yes
    sudo postconf -e smtp_sasl_password_maps=hash:/etc/postfix/sasl_passwd
    sudo postconf -e smtp_sasl_security_options=noanonymous
    sudo postconf -e smtp_sasl_tls_security_options=noanonymous
    sudo postconf -e smtp_sasl_mechanism_filter='AUTH LOGIN'
    sudo postconf -e unknown_local_recipient_reject_code=550
    sudo postconf -e owner_request_special=no
    sudo postconf -e transport_maps='regexp:/opt/mailman/core/var/data/postfix_lmtp'
    sudo postconf -e local_recipient_maps='regexp:/opt/mailman/core/var/data/postfix_lmtp'
    sudo postconf -e relay_domains='regexp:/opt/mailman/core/var/data/postfix_domains'

Restart postfix to apply changes.

    sudo systemctl restart postfix


### Configure cron jobs

Some actions needs to be triggered on a regular basis. But since Docker
containers are not intended for running background jobs we let the host
do the work.

Configure system crontab by running:

    $ sudo crontab -e

Then add the following to the bottom of the file.

    0 18 * * * docker-compose -f </full/path/to/docker-compose.yaml> exec mailman-core /usr/bin/mailman digests --periodic
    0 10 * * * docker-compose -f </full/path/to/docker-compose.yaml> exec mailman-core /usr/bin/mailman notify

You may update the cron timer to your preferences. In the example above
digests are sent out at 18:00 and moderators are notified at 10:00 to
any actions they need to take, like approving new subscriptions.


### Start Mailman3

Now it's time to launch the service.

    docker-compose up -d

After a minute or so Mailman3 should be responding.
Check it out at the domain you chose.


## References

- https://asynchronous.in/docker-mailman/
- https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script
- https://certbot.eff.org/
- https://xiaoxing.us/2018/01/01/deploy-mailman-3-on-aws-using-docker/
- https://www.digitalocean.com/community/tutorials/how-to-set-up-a-mail-relay-with-postfix-and-mailgun-on-ubuntu-16-04
- https://docs.mailman3.org/en/latest/config-core.html#configuring-cron-jobs
