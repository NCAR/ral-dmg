The RAL Data Management Group (LDM and more)


Structure of this repository
```
common
machines
├── curry
├── oregano
├── parsley
├── gateway # shared oregano/parsley files
├── thyme

Each machine/common has:
etc  -- ldm configuration files
bin  -- scripts and other executables
param -- configuration files
env -- environment variables, bashrc
control -- crontab

```

# Installation
* For LDM machines bin and params are copied into ~/utils


# Copy and Paste
```
mkdir -p ~/git
cd ~/git
git clone https://github.com/prestopUCAR/ral-dmg.git
cd ral-dmg
```

