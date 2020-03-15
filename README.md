# pyaltitude

Depends on Altitude server patches from https://gitlab.com/sdizazzo/server_patches which is a just a minor fork of the work done by Xal.  Simple `make` should compile it, then copy `game.jar` over the existsing one, and `mods.hjson`  and `permissions.hjson` into the `altitude/servers` directory 

__Dependencies:__

- python3.7
- ujson
- pyyaml
- inotify_simple
