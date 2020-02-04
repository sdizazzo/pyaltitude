class Attach(object):
    #after we have fun playing around with it, lock it down to same
            #team only
            #NOTE In some games we might also wnat to consider limiting attach
            # to only certain plane types
            if from_player.team and from_player.team == 2:
                await from_player.whisper("Can't attach from spec")
                return
            if to_player.team and to_player.team == 2:
                await from_player.whisper("Can't attach to a player in spec")
                return
            if not to_player.is_alive():
                await from_player.whisper("Can't attach. %s is dead!" % to_player.nickname)
                return
            if from_player.attached:
                await from_player.whisper("You've already attached once this life!")
                return

            #if from_player == to_player:
            #    await from_player.whisper('Not a chance!!')
            #    return
            #elif not from_player.team == to_player.team:
            #    from_player.whisper('You can only attach to members of your own team!')
            #    return
            await from_player.whisper('Attaching to %s' % to_player.nickname)
            await to_player.whisper('%s is attaching to you!' % from_player.nickname)
            await server.overrideSpawnPoint(from_player.nickname, to_player.x, to_player.y, 0)
            from_player.attached = True
            # pass x=0,y=0,angle=0 to clear the override and resume normal
            # spawning rules for a target player, otherwise overrides are
            # cleared on map change (after "mapLoading" but before "mapChange")
            # and on player disconnection

            #spawnPoint is reset with 'spawn' event
