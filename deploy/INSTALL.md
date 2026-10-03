# Install on the RTV server (VM 513)

```
sudo git clone https://github.com/Raise-the-Voices/volkit /opt/volkit-src
sudo mkdir -p /opt/volkit && sudo cp /opt/volkit-src/deploy/ansible/example-vars.yml /opt/volkit/vars.yml && sudo chmod 600 /opt/volkit/vars.yml
sudo nano /opt/volkit/vars.yml
cd /opt/volkit-src && sudo ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml -e @/opt/volkit/vars.yml
systemctl status volkit
```

## Prompt for a Claude session on the server

```
CONSTRAINT: do NOT point to demo in anything. No demos.linkedtrust.us or any demo host in config, nav, links, docs or code.
CONSTRAINT: the Ansible playbook in the repo is the record of the deploy. Run it on this server; any step done by hand goes back into the playbook, pushed.

You are on the RTV server (VM 513, 10.0.0.163). It runs Taiga (tasks.), Marten (help.) and Ghost (raisethevoices.org). Do not change or restart them.
Goal: deploy VolKit, the RTV volunteer dashboard: https://github.com/Raise-the-Voices/volkit. Read README.md and deploy/ansible/.

Check and report first: free memory/disk; python3 --version (needs 3.10+); port 8010 free (Taiga uses 8000, 8003, 8888); ansible installed (ask before installing); git push access to GitHub (Raise-the-Voices, Cooperation-org); nginx gets its own vhost only.

Ask the project owner, one line each:
- Hostname under raisethevoices.org (DNS and Caddy are set on the Proxmox host).
- DB: ask the project owner to run on the Proxmox host: sudo ~/cobox/scripts/create-app-db.sh volkit. Never local Postgres, never SSH to VM 100.
- LinkedTrust OIDC client, redirect https://<host>/auth/linkedtrust/callback.
- Ghost Content key (+ Admin key for drafts). Unset = card off, fine to ship.

Then:
1. Clone; copy example-vars.yml to /opt/volkit/vars.yml (chmod 600, never committed); fill in.
2. sudo ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml -e @/opt/volkit/vars.yml
3. Use it as a volunteer: sign in, click every top link and card link, check phone width. Fix in the repo, push to main.
4. Registry: clone github.com/Cooperation-org/cobox, add VolKit to the VM 513 row in app-registry.md, push.

Not yours: "To do next" (Taiga) waits on baobab; cases stays a link. Framework problems: github.com/Cooperation-org/baobab, SCRATCH.md (format at its top).
Done: a volunteer signs in at the hostname, registry pushed, URL on its own line in your last reply.
```
