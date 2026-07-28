# check_multi 2.0 Alpha – Installation Guide

## 1. Prerequisites

| Component          | Required | Notes                                      | Typical Install Command                  |
|--------------------|----------|--------------------------------------------|------------------------------------------|
| bash ≥ 4.2         | Yes      | Most modern Linux/macOS systems            | pre-installed                            |
| OpenSSH client     | Yes      | `ssh` command                              | `openssh-client` / `openssh`             |
| python3 ≥ 3.8      | Optional | Only needed for `--excel` reports          | `python3`                                |
| openpyxl           | Optional | Excel report generation                    | `pip install openpyxl`                   |
| yq                 | Recommended | YAML config parsing                      | See below                                |
| shellcheck         | Dev only | Static analysis                            | `shellcheck`                             |
| bats               | Dev only | Test framework                             | `bats`                                   |
| sshpass            | Optional | Only if you must use password auth         | `sshpass` (discouraged)                  |

### Installing yq (recommended)

```bash
# Linux (amd64)
sudo wget -qO /usr/local/bin/yq \
  https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq

# macOS (Homebrew)
brew install yq
```

### Installing openpyxl (for Excel reports)

```bash
python3 -m pip install --user openpyxl
# or inside a virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install openpyxl
```

---

## 2. Installation Methods

### Method A – Git Clone (Recommended)

```bash
git clone https://github.com/<your-org>/check_multi.git
cd check_multi

chmod 0755 bin/check_multi
export PATH="$PWD/bin:$PATH"
check_multi --version
```

### Method B – Release Tarball / Zip

```bash
tar xzf check_multi-2.0.0-alpha.tar.gz
cd check_multi_2.0
chmod 0755 bin/check_multi
./bin/check_multi --version
```

### Method C – User-local install (no root)

```bash
mkdir -p ~/bin ~/opt
cp -a check_multi_2.0 ~/opt/check_multi
ln -sf ~/opt/check_multi/bin/check_multi ~/bin/check_multi
export PATH="$HOME/bin:$PATH"
check_multi --version
```

### Method D – System-wide install (requires root)

```bash
sudo mkdir -p /opt/check_multi
sudo cp -a . /opt/check_multi/
sudo ln -sf /opt/check_multi/bin/check_multi /usr/local/bin/check_multi
sudo chmod 0755 /usr/local/bin/check_multi
check_multi --version
```

---

## 3. Post-Install Verification

```bash
check_multi --version
check_multi --help
check_multi --dry-run platform examples/devices.txt
check_multi --dry-run --excel platform examples/devices.txt
```

---

## 4. SSH Key Setup (Strongly Recommended)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/check_multi -C "check_multi-audit"
ssh-copy-id -i ~/.ssh/check_multi.pub admin@f5-lab-01.example.com
ssh -i ~/.ssh/check_multi admin@f5-lab-01.example.com "tmsh show sys version"
```

---

## 5. Common Installation Issues

| Symptom                              | Likely Cause                     | Fix                                      |
|--------------------------------------|----------------------------------|------------------------------------------|
| `yq: command not found`              | yq not installed                 | Install yq (see above)                   |
| Excel report fails                   | openpyxl missing                 | `pip install openpyxl`                   |
| `Permission denied` on bin/check_multi | Not executable                 | `chmod 0755 bin/check_multi`             |
| `Check module not found`             | Wrong working directory          | Run from the repo root or set PATH       |
| Host key warnings                    | Expected in lab profile          | Use `-e prod` or set strict checking     |

---

## 6. Uninstall

```bash
# User-local
rm -rf ~/opt/check_multi
rm -f ~/bin/check_multi

# System-wide
sudo rm -rf /opt/check_multi
sudo rm -f /usr/local/bin/check_multi
```
