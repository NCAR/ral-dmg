The RAL Data Management Group (LDM and more)


Structure of this repository
```
inflight-icing
rapdmg
common

Under inflight-icing,rapdmg (other projects welcome to create directories at this level also) are directories with user names (ldm, rapdmg, etc.), then under the user names:
common
machines
├── curry
├── oregano
├── parsley
├── gateway # shared oregano/parsley files
├── thyme

Under each machine/common 
etc  -- ldm configuration files
bin  -- scripts and other executables
param -- configuration files
control -- crontab, environment variables, bashrc

So:
$project/$user/$machine/dirs

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

