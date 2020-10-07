The RAL Data Management Group (LDM and more)


# Structure of this repository

In general directories in this repository are structured like: $PROJECT/$USER/$MACHINE

At any level, there can be a directory named 'common' that holds files that are common across multiple projects, users, machines, etc.

For example:
 * Project:
   * inflight-icing
   * rapdmg
   * common

Users:
* ldm
* rapdmg

Machines:
* curry
* oregano
* parsley
* gateway # shared oregano/parsley files
* thyme


Common directories under machines 
* etc  -- ldm configuration files
* bin  -- scripts and other executables
* param -- configuration files
* control -- crontab, environment variables, bashrc



# Installation
* For LDM machines bin and params are copied into ~/utils


# Copy and Paste
```
PROJECT=rapdmg
USER=ldm
MACHINE=curry 
mkdir -p ~/git
cd ~/git
git clone https://github.com/prestopUCAR/ral-dmg.git
cd ral-dmg

ln -s $PROJECT/$USER/common/bin/* ~/util/bin/
ln -s $PROJECT/$USER/common/param/* ~/util/param/
ln -s $PROJECT/$USER/common/control/crontab ~/
ln -s $PROJECT/$USER/common/control/bashrc ~/.bashrc
ln -s $PROJECT/$USER/common/etc/* ~/etc

ln -s $PROJECT/$USER/$MACHINE/bin/* ~/util/bin/
ln -s $PROJECT/$USER/$MACHINE/param/* ~/util/param/
ln -s $PROJECT/$USER/$MACHINE/control/crontab ~/
ln -s $PROJECT/$USER/$MACHINE/control/bashrc ~/.bashrc
ln -s $PROJECT/$USER/$MACHINE/etc/* ~/etc

```

