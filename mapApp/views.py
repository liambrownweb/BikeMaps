from django.shortcuts import render, get_object_or_404

from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, Point, fromstr

from mapApp.models import Incident
from mapApp.forms import IncidentForm

def index(request):
	if request.method == 'POST':
		form = IncidentForm(request.POST)
		
		# Copy to allow mutation of value
		form.data = form.data.copy()

		# Convert string coords to valid geometry object
		pnt = fromstr(form.data['point'])
		form.data['point'] = GEOSGeometry(pnt)
		

		if form.is_valid():
			form.save()		# create object
			#	redirect to index again or to "thank you" page
			form = IncidentForm() # Clean form
		else:
			errors = form.errors
			# 	Display index with form open and error messages

	else:
		form = IncidentForm()

	context = {
		'incidents': Incident.objects.all(),
		"form": form, 	#the form to be rendered
		"completion_p": 60,	#load bar percentage. Not implemented
		# "next_action":
	}
	return render(request, 'mapApp/index.html', context)


def about(request):
	context = {
		'incidents': Incident.objects.all(),
	}

	return render(request, 'mapApp/about.html', context)

def sponsors(request):
	return render(request, 'mapApp/sponsors.html')

def contact(request):
	return render(request, 'mapApp/contact.html')

# def detail(request, poll_id):
#     poll = get_object_or_404(Poll, pk=poll_id)
#     return render(request, 'polls/detail.html', {'poll': poll})

# def results(request, poll_id):
#     poll = get_object_or_404(Poll, pk=poll_id)
#     return render(request, 'polls/results.html', {'poll': poll})

# def vote(request, poll_id):
#     p = get_object_or_404(Poll, pk=poll_id)
#     try:
#         selected_choice = p.choice_set.get(pk=request.POST['choice'])
#     except (KeyError, Choice.DoesNotExist):
#         # Redisplay the poll voting form.
#         return render(request, 'polls/detail.html', {
#             'poll': p,
#             'error_message': "You didn't select a choice.",
#         })
#     else:
#         selected_choice.votes += 1
#         selected_choice.save()
#         # Always return an HttpResponseRedirect after successfully dealing
#         # with POST data. This prevents data from being posted twice if a
#         # user hits the Back button.
#         return HttpResponseRedirect(reverse('polls:results', args=(p.id,)))
