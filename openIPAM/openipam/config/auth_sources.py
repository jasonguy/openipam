from openipam.config import auth
import openipam.backend.auth.interfaces
from openipam.utilities import error

if auth.interfaces:
	interfaces = auth.interfaces
else:
	# FIXME
	interfaces = {}
	
	if auth.internal_enabled:
		interfaces[auth.sources.INTERNAL] = openipam.backend.auth.interfaces.InternalAuthInterface()
		
	if auth.ldap_enabled:
		interfaces[auth.sources.LDAP] = openipam.backend.auth.interfaces.LDAPInterface()

def get_info( username ):
	info = auth.dbi.get_users(username=username)
	if not info:
		# FIXME: do we want this to search LDAP if ldap_auto_create is
		# set? If so, it will create the user in the DB if a search is
		# performed... which may not be a bad thing
		return None
	auth_sources = [ i['source'] for i in info ]
	for src in auth_sources:
		iface = interfaces[src]
		try:
			user = iface.verify(username)
			return user

		except error.NotUser:
			# If this user doesn't exist for this auth source, just move on
			pass
		except error.NoEmail:
			# Raise an error if the backend auth requires email address to be set and it is not
			raise
	return None

def authenticate( username, password ):
	auth_interface, userfoo = _verify( username )	
	# This will raise an exception if the password is wrong
	user = auth_interface.authenticate(username, password.encode('utf8'))
	return user

def verify( username ):
	auth_interface, user = _verify(username)
	return user

def _verify( username ):
	user = auth.dbi.get_users(username=username)
	
	if not user and not auth.ldap_auto_create:
		raise error.NotUser('User does not exist in DB.')
	
	auth_sources = [ i['source'] for i in user ]
	
	if auth.ldap_auto_create and auth.sources.LDAP not in auth_sources:
		auth_sources.append( auth.sources.LDAP )
			
	auth_interface = None
	
	for src in auth_sources:
		iface = interfaces[src]
		try:
			user = iface.verify(username)
		
			# If here, then the user exists in this auth source
			# Save the right auth interface for use below
			auth_interface = iface
			break
		except error.NotUser:
			# If this user doesn't exist for this auth source, just move on
			pass
	
	if not auth_interface:
		# FIXME: NotUser might be a better exception here
		raise error.NotImplemented("No other authentication types implemented")

	return auth_interface, user

def valid_password(password):
	if len(password) < 8:
		raise error.InvalidArgument('Passwords must be at least 8 chars')

def create_user( **kw ):
	source = kw['source']
	del kw['source']
	valid_password(kw['password'])
	source = getattr(auth.sources,source)
	interface = interfaces[source]
	return interface.create_user(**kw)

def update_password( username, password, old_password=None ):
	interface, user = _verify(username)
	valid_password(password)
	return interface.update_password(username=username, password=password, old_password=old_password)


