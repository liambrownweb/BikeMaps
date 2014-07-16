from django.shortcuts import get_object_or_404, render

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry
from django.contrib import messages
from django.core.mail import send_mail

from django.contrib.auth.models import User, Group
from mapApp.models import Incident, Route, AlertArea, AlertNotification
from mapApp.forms import IncidentForm, RouteForm, EmailForm, GeofenceForm, EditAlertAreaForm

# Used for downloading data
from spirit.utils.decorators import administrator_required
from django.contrib.auth.decorators import login_required
from djgeojson.serializers import Serializer as GeoJSONSerializer
import time


def index(request, lat=None, lng=None, zoom=None):
	context = {
		'incidents': Incident.objects.all(),
		"incidentForm": IncidentForm(), 	#the form to be rendered

		"routes": Route.objects.all(),
		"routeForm": RouteForm(),

		"geofences": AlertArea.objects.filter(user=request.user.id),
		"geofenceForm": GeofenceForm(),
		"geofenceEditForm": EditAlertAreaForm()
	}

	if(lat is not None and lng is not None and zoom is not None):
		context['lat']= float(lat)
		context['lng']= float(lng)
		context['zoom']= int(zoom)
	
	return render(request, 'mapApp/index.html', context)


def about(request):
	return render(request, 'mapApp/about.html', {"emailForm": EmailForm()})


def contact(request):
	if request.method == 'POST':
		emailForm = EmailForm(request.POST)

		if emailForm.is_valid():
			subject = emailForm.cleaned_data['subject']
			message = emailForm.cleaned_data['message']
			sender = emailForm.cleaned_data['sender']
			cc_myself = emailForm.cleaned_data['cc_myself']

			contact_group = Group.objects.get(name="admin contact")
			members = contact_group.user_set.all()
			recipients = []
			for r in members:
				recipients.append(r.email) 
			if cc_myself:
				recipients.append(sender)

			send_mail(subject, message, sender, recipients)

			messages.success(request, '<strong>Thank you!</strong><br>We\'ll do our best to get back to you.')
		
		else:
			# Form is not valid, display modal with highlighted errors 
			return render(request, 'mapApp/about.html', {
				"emailForm": emailForm,
			})
	
	return HttpResponseRedirect(reverse('mapApp:about')) 


def postRoute(request):
	if request.method == 'POST':
		routeForm = RouteForm(request.POST)

		# Convert string coords to valid geometry object
		routeForm.data = routeForm.data.copy()
		routeForm.data['line'] = GEOSGeometry(routeForm.data['line'])

		if routeForm.is_valid():
			routeForm.save()
			messages.success(request, '<strong>Thank you!</strong><br>Your route was successfully added.')

		else:
			# Form is not valid, display modal with highlighted errors 
			return render(request, 'mapApp/index.html', {
				'incidents': Incident.objects.all(),
				"incidentForm": IncidentForm(),

				"geofences": AlertArea.objects.filter(user=request.user.id),
				"geofenceForm": GeofenceForm(),
				"geofenceEditForm": EditAlertAreaForm(),

				"routes": Route.objects.all(),
				"routeForm": routeForm,
			})
	
	return HttpResponseRedirect(reverse('mapApp:index')) 


def postIncident(request):
	if request.method == 'POST':
		incidentForm = IncidentForm(request.POST)
		
		# Convert string coords to valid geometry object
		incidentForm.data = incidentForm.data.copy()
		incidentForm.data['geom'] = GEOSGeometry(incidentForm.data['geom'])

		if incidentForm.is_valid():
			incident = incidentForm.save()
			addPointToUserAlerts(request, incident)

			messages.success(request, '<strong>Thank you!</strong><br>Your incident marker was successfully added.')
			return HttpResponseRedirect(reverse('mapApp:index', kwargs=({"lat":str(incident.latlngList()[0]), "lng":str(incident.latlngList()[1]), "zoom":str(16)}))) 
		
		else:
			# Form is not valid, display modal with highlighted errors 
			return render(request, 'mapApp/index.html', {
				'incidents': Incident.objects.all(),
				"incidentForm": incidentForm,

				"geofences": AlertArea.objects.filter(user=request.user.id),
				"geofenceForm": GeofenceForm(),
				"geofenceEditForm": EditAlertAreaForm(),
				
				"routes": Route.objects.all(),
				"routeForm": RouteForm(),
			})
	
	else:
		return HttpResponseRedirect(reverse('mapApp:index')) 

def addPointToUserAlerts(request, incident):
	intersectingPolys = AlertArea.objects.filter(geom__intersects=incident.geom) #list of AlertArea objects
	usersToAlert = list(set([poly.user for poly in intersectingPolys])) # get list of distinct users to alert

	if (incident.incident_type() == "Collision"):
		action = 0
	elif (incident.incident_type() == "Near miss"):
		action = 1
	else:
		action = 2

	for user in usersToAlert:
		AlertNotification(user=user, point=incident, action=action).save()

	return

@login_required
def postAlertPolygon(request):
	if request.method == 'POST':
		geofenceForm = GeofenceForm(request.POST)
		
		# Convert string coords to valid geometry object
		geofenceForm.data = geofenceForm.data.copy()
		geofenceForm.data['geom'] = GEOSGeometry(geofenceForm.data['geom'])
		
		geofenceForm.data['user'] = request.user.id

		if geofenceForm.is_valid():
			geofenceForm.save()
			messages.success(request, 'You will now recieve alerts for the area was traced.')
			return HttpResponseRedirect(reverse('mapApp:index')) 
		
		else:
			# Form is not valid, display modal with highlighted errors 
			return render(request, 'mapApp/index.html', {
				'incidents': Incident.objects.all(),
				"incidentForm": IncidentForm(),
				"incidentFormErrors": False,

				"geofence": AlertArea.objects.filter(user=request.user.id),
				"geofenceForm": geofenceForm,
				"geofenceFormErrors": True,
				"geofenceEditForm": EditAlertAreaForm(),
				
				"routes": Route.objects.all(),
				"routeForm": RouteForm(),
				"routeFormErrors": False
			})
	
	else:
		return HttpResponseRedirect(reverse('mapApp:index'))



@administrator_required
def getIncidents(request):
	data = GeoJSONSerializer().serialize(Incident.objects.all(), indent=2, use_natural_keys=True)
	
	response = HttpResponse(data, content_type="application/json")
	response['Content-Disposition'] = 'attachment; filename="bikemaps_incidents_%s.json' % time.strftime("%x_%H-%M")
	return response


@login_required
def readAlertPoint(request, alertID):
	alert = get_object_or_404(AlertNotification.objects.filter(user=request.user), pk=alertID)
	if (alert):
		alert.is_read=True
		alert.save()

		return HttpResponseRedirect(reverse('mapApp:index', kwargs=({"lat":str(alert.point.latlngList()[0]), "lng":str(alert.point.latlngList()[1]), "zoom":str(18)}) ))
	else:
		return HttpResponseRedirect(reverse('mapApp:index')) 


@login_required
def editAlertArea(request):
	if(request.method == 'POST'):
		editForm = EditAlertAreaForm(request.POST)
		
		if editForm.is_valid():
			editType = editForm.cleaned_data['editType']
			polyEdited = get_object_or_404(AlertArea.objects.filter(user=request.user), pk=editForm.cleaned_data['editPk'])

			if(editType == 'edit'):
				polyEdited.geom = GEOSGeometry(editForm.cleaned_data['editGeom'])	# edit the object geometry
				polyEdited.save()
				messages.success(request, 'Alert Area was edited')
		
			elif (editType == 'delete'):
				polyEdited.delete() 	# delete the object
				messages.success(request, 'Alert Area was deleted')
			
	return HttpResponseRedirect(reverse('mapApp:index'))