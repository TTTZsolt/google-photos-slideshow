#!/data/data/com.termux/files/usr/bin/bash
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE71nfg/Xh13D7uR7g0QwLh11r5b6q0SrTBAlROD+9wu claude-code-remote@hul-0185" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
echo "Kesz - a kulcs hozzaadva."
