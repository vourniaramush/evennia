"""
This module provides a set of permission lock functions for use
with Evennia's permissions system.

To call these locks, make sure this module is included in the
settings tuple PERMISSION_FUNC_MODULES then define a lock on the form 
'<access_type>:func(args)' and add it to the object's lockhandler. 
Run the access() method of the handler to execute the lock check. 

Note that accessing_obj and accessed_obj can be any object type
with a lock variable/field, so be careful to not expect
a certain object type. 


Appendix: MUX locks

Below is a list nicked from the MUX help file on the locks available
in standard MUX. Most of these are not relevant to core Evennia since
locks in Evennia are considerably more flexible and can be implemented
on an individual command/typeclass basis rather than as globally
available like the MUX ones. So many of these are not available in
basic Evennia, but could all be implemented easily if needed for the
individual game.

MUX Name:      Affects:        Effect:                                         
-------------------------------------------------------------------------------
DefaultLock:   Exits:          controls who may traverse the exit to
                               its destination.
                                 Evennia: "traverse:<lockfunc()>"
               Rooms:          controls whether the player sees the SUCC
                               or FAIL message for the room following the
                               room description when looking at the room.
                                 Evennia: Custom typeclass
               Players/Things: controls who may GET the object.
                                 Evennia: "get:<lockfunc()"
 EnterLock:    Players/Things: controls who may ENTER the object
                                 Evennia: 
 GetFromLock:  All but Exits:  controls who may gets things from a given
                               location.
                                 Evennia: 
 GiveLock:     Players/Things: controls who may give the object.
                                 Evennia:  
 LeaveLock:    Players/Things: controls who may LEAVE the object.
                                 Evennia: 
 LinkLock:     All but Exits:  controls who may link to the location if the
                               location is LINK_OK (for linking exits or
                               setting drop-tos) or ABODE (for setting
                               homes)
                                 Evennia: 
 MailLock:     Players:        controls who may @mail the player.
                               Evennia: 
 OpenLock:     All but Exits:  controls who may open an exit.
                                 Evennia:  
 PageLock:     Players:        controls who may page the player.
                                 Evennia: "send:<lockfunc()>"
 ParentLock:   All:            controls who may make @parent links to the
                               object.
                                 Evennia: Typeclasses and "puppet:<lockstring()>"
 ReceiveLock:  Players/Things: controls who may give things to the object.
                                 Evennia: 
 SpeechLock:   All but Exits:  controls who may speak in that location
                                 Evennia: 
 TeloutLock:   All but Exits:  controls who may teleport out of the
                               location.
                                 Evennia: 
 TportLock:    Rooms/Things:   controls who may teleport there
                                 Evennia:  
 UseLock:      All but Exits:  controls who may USE the object, GIVE the
                               object money and have the PAY attributes
                               run, have their messages heard and possibly
                               acted on by LISTEN and AxHEAR, and invoke
                               $-commands stored on the object.
                                 Evennia: Commands and Cmdsets. 
 DropLock:     All but rooms:  controls who may drop that object.
                                 Evennia:
 VisibleLock:  All:            Controls object visibility when the object
                               is not dark and the looker passes the lock.
                               In DARK locations, the object must also be
                               set LIGHT and the viewer must pass the
                               VisibleLock.
                                 Evennia: Room typeclass with Dark/light script
"""

from django.conf import settings
from src.utils import search
from src.utils import utils

PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]

def _to_player(accessing_obj):
    "Helper function. Makes sure an accessing object is a player object"
    if utils.inherits_from(accessing_obj, "src.objects.objects.Object"):
        # an object. Convert to player.
        accessing_obj = accessing_obj.player
    return accessing_obj


# lock functions 

def true(*args, **kwargs):
    "Always returns True."
    return True
def all(*args, **kwargs):
    return True 
def false(*args, **kwargs):
    "Always returns False"
    return False 
def none(*args, **kwargs):
    return False 

def perm(accessing_obj, accessed_obj, *args, **kwargs):
    """
    The basic permission-checker. Ignores case. 

    Usage: 
       perm(<permission>)
    
    where <permission> is the permission accessing_obj must
    have in order to pass the lock. If the given permission 
    is part of PERMISSION_HIERARCHY, permission is also granted
    to all ranks higher up in the hierarchy. 
    """
    if not args:
        return False 
    perm = args[0].lower()
    if hasattr(accessing_obj, 'permissions'):
        if perm in [p.lower() for p in accessing_obj.permissions]:
            # simplest case - we have a direct match
            return True 
        if perm in PERMISSION_HIERARCHY:
            # check if we have a higher hierarchy position
            ppos = PERMISSION_HIERARCHY.index(perm)
            return any(True for hpos, hperm in enumerate(PERMISSION_HIERARCHY) 
                       if hperm in [p.lower() for p in accessing_obj.permissions] and hpos > ppos)
    return False 

def perm_above(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only allow objects with a permission *higher* in the permission
    hierarchy than the one given. If there is no such higher rank, 
    it's assumed we refer to superuser. If no hierarchy is defined,
    this function has no meaning and returns False. 
    """
    if args and args[0].lower() in PERMISSION_HIERARCHY:
        ppos = PERMISSION_HIERARCHY.index(args[0].lower())
        return any(True for hpos, hperm in enumerate(PERMISSION_HIERARCHY)
                   if hperm in [p.lower() for p in accessing_obj.permissions] and hpos > ppos)

def pperm(accessing_obj, accessed_obj, *args, **kwargs):
    """
    The basic permission-checker for Player objects. Ignores case. 

    Usage: 
       pperm(<permission>)
    
    where <permission> is the permission accessing_obj must
    have in order to pass the lock. If the given permission 
    is part of PERMISSION_HIERARCHY, permission is also granted
    to all ranks higher up in the hierarchy. 
    """
    return perm(_to_player(accessing_obj), accessed_obj, *args, **kwargs)

def pperm_above(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only allow Player objects with a permission *higher* in the permission
    hierarchy than the one given. If there is no such higher rank, 
    it's assumed we refer to superuser. If no hierarchy is defined,
    this function has no meaning and returns False. 
    """
    return perm_above(_to_player(accessing_obj), accessed_obj, *args, **kwargs)

def dbref(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      dbref(3)
    
    This lock type checks if the checking object
    has a particular dbref. Note that this only
    works for checking objects that are stored
    in the database (e.g. not for commands)
    """
    if not args:
        return False
    try:
        dbref = int(args[0].strip().strip('#'))
    except ValueError:
        return False
    if hasattr(accessing_obj, 'id'):
        return dbref == accessing_obj.id
    return False 

def pdbref(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Same as dbref, but making sure accessing_obj is a player.
    """
    return dbref(_to_player(accessing_obj), accessed_obj, *args, **kwargs)

def id(accessing_obj, accessed_obj, *args, **kwargs):
    "Alias to dbref"
    return dbref(accessing_obj, accessed_obj, *args, **kwargs)

def pid(accessing_obj, accessed_obj, *args, **kwargs):
    "Alias to dbref, for Players"
    return dbref(_to_player(accessing_obj), accessed_obj, *args, **kwargs)


def attr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      attr(attrname)
      attr(attrname, value)
      attr(attrname, value, compare=type)

    where compare's type is one of (eq,gt,lt,ge,le,ne) and signifies
    how the value should be compared with one on accessing_obj (so
    compare=gt means the accessing_obj must have a value greater than
    the one given).
    
    Searches attributes *and* properties stored on the checking
    object. The first form works like a flag - if the attribute/property
    exists on the object, it returns True. The second form also requires
    that the value of the attribute/property matches. Note that all
    retrieved values will be converted to strings before doing the comparison.     
    """
    # deal with arguments 
    if not args:
        return False
    attrname = args[0].strip()
    value = None 
    if len(args) > 1:
        value = args[1].strip()
    compare = 'eq'
    if kwargs:
        compare = kwargs.get('compare', 'eq')

    def valcompare(val1, val2, typ='eq'):
        "compare based on type"
        try:
            if typ == 'eq':
                return val1 == val2 or int(val1) == int(val2)
            elif typ == 'gt':
                return int(val1) > int(val2)
            elif typ == 'lt':
                return int(val1) < int(val2)
            elif typ == 'ge':
                return int(val1) >= int(val2)
            elif typ == 'le':
                return int(val1) <= int(val2)
            elif typ == 'ne':
                return int(val1) != int(val2)
            else:
                return False 
        except Exception, e:
            print e
            # this might happen if we try to compare two things that cannot be compared
            return False 

    # first, look for normal properties on the object trying to gain access    
    if hasattr(accessing_obj, attrname):
        if value:
            return valcompare(str(getattr(accessing_obj, attrname)), value, compare)
        return True 
    # check attributes, if they exist    
    if (hasattr(accessing_obj, 'has_attribute') 
        and accessing_obj.has_attribute(attrname)):
        if value:
            return (hasattr(accessing_obj, 'get_attribute') 
                    and valcompare(accessing_obj.get_attribute(attrname), value, compare))
        return True 
    return False 

def objattr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      objattr(attrname)
      objattr(attrname, value)
      objattr(attrname, value, compare=type)

    Works like attr, except it looks for an attribute on 
    accessing_obj.obj, if such an entity exists. Suitable
    for commands.

    """
    if hasattr(accessing_obj, "obj"):
        return attr(accessing_obj.obj, accessed_obj, *args, **kwargs)

def locattr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      locattr(attrname)
      locattr(attrname, value)
      locattr(attrname, value, compare=type)

    Works like attr, except it looks for an attribute on 
    accessing_obj.location, if such an entity exists. Suitable
    for commands.

    """
    if hasattr(accessing_obj, "location"):
        return attr(accessing_obj.location, accessed_obj, *args, **kwargs)


def attr_eq(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)
    """
    return attr(accessing_obj, accessed_obj, *args, **kwargs)

def attr_gt(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)

    Only true if access_obj's attribute > the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{'compare':'gt'})
def attr_ge(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)

    Only true if access_obj's attribute >= the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{'compare':'ge'})
def attr_lt(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)

    Only true if access_obj's attribute < the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{'compare':'lt'})
def attr_le(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)

    Only true if access_obj's attribute <= the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{'compare':'le'})
def attr_ne(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: 
       attr_gt(attrname, 54)

    Only true if access_obj's attribute != the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{'compare':'ne'})

def holds(accessing_obj, accessed_obj, objid, *args, **kwargs):
    """
    Usage: 
       holds(object_id)

    This is passed if accessing_obj 'contains' an object with the given
    key name or dbref. 
    """
    dbref = utils.dbref(objid)
    contains = accessing_obj.contains 
    if dbref and any((True for obj in contains if obj.id == dbref)):
        return True 
    objid = objid.lower()
    return any((True for obj in contains if obj.name.lower() == objid))

def carried(accessing_obj, accessed_obj):
    """
    Usage: 
      carried()

    This is passed if accessed_obj is carried by accessing_obj (that is,
    accessed_obj.location == accessing_obj)
    """
    return hasattr(accessed_obj, "location") and accessed_obj.location == accessing_obj

def objcarried(accessing_obj, accessed_obj):
    """
    Usage:
      objcarried()

    Like carried, except this lock looks for a property "obj" on the accessed_obj
    and tries to determing if *this* is carried by accessing_obj. This works well
    for commands and scripts. 
    """
    return hasattr(accessed_obj, "obj") and accessed_obj.obj and \
        hasattr(accessed_obj.obj, "location") and accessed_obj.obj.location == accessing_obj

def superuser(*args, **kwargs):
    """
    Only accepts an accesing_obj that is superuser (e.g. user #1)
    
    Since a superuser would not ever reach this check (superusers
    bypass the lock entirely), any user who gets this far cannot be a
    superuser, hence we just return False. :)
    """
    return False 
    
def serversetting(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only returns true if the Evennia settings exists, alternatively has a certain value.
    
    Usage:
      serversetting(IRC_ENABLED)
      serversetting(BASE_SCRIPT_PATH, [game.gamesrc.scripts])

    A given True/False or integers will be converted properly.
    """
    if not args:
        return False
    if len(args) < 2:
        setting = args[0]
        val = "True" 
    else:
        setting, val = args[0], args[1]
    # convert
    if val == 'True':
        val = True
    elif val == 'False':
        val = False 
    elif val.isdigit():
        val = int(val)
    if setting in settings._wrapped.__dict__:
        return settings._wrapped.__dict__[setting] == val
    return False 