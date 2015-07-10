from __future__ import absolute_import, unicode_literals

from json import dumps, loads

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.utils import timezone, translation
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from documents.search import document_search

from .classes import MissingItem
from .forms import (
    LicenseForm, LocaleProfileForm, LocaleProfileForm_view,
    UserForm, UserForm_view
)
from .generics import *  # NOQA
from .menus import menu_tools, menu_setup


class AboutView(TemplateView):
    template_name = 'appearance/about.html'


class CurrentUserDetailsView(TemplateView):
    template_name = 'appearance/generic_form.html'

    def get_context_data(self, **kwargs):
        data = super(CurrentUserDetailsView, self).get_context_data(**kwargs)
        data.update({
            'form': UserForm_view(instance=self.request.user),
            'read_only': True,
            'title': _('Current user details'),
        })
        return data


class CurrentUserEditView(SingleObjectEditView):
    extra_context = {'title': _('Edit current user details')}
    form_class = UserForm
    post_action_redirect = reverse_lazy('common:current_user_details')

    def get_object(self):
        return self.request.user


class CurrentUserLocaleProfileDetailsView(TemplateView):
    template_name = 'appearance/generic_form.html'

    def get_context_data(self, **kwargs):
        data = super(CurrentUserLocaleProfileDetailsView, self).get_context_data(**kwargs)
        data.update({
            'form': LocaleProfileForm_view(instance=self.request.user.locale_profile),
            'read_only': True,
            'title': _('Current user locale profile details'),
        })
        return data


class CurrentUserLocaleProfileEditView(SingleObjectEditView):
    extra_context = {'title': _('Edit current user locale profile details')}
    form_class = LocaleProfileForm
    post_action_redirect = reverse_lazy('common:current_user_locale_profile_details')

    def form_valid(self, form):
        form.save()

        timezone.activate(form.cleaned_data['timezone'])
        translation.activate(form.cleaned_data['language'])

        if hasattr(self.request, 'session'):
            self.request.session[translation.LANGUAGE_SESSION_KEY] = form.cleaned_data['language']
            self.request.session[settings.TIMEZONE_SESSION_KEY] = form.cleaned_data['timezone']
        else:
            self.request.set_cookie(settings.LANGUAGE_COOKIE_NAME, form.cleaned_data['language'])
            self.request.set_cookie(settings.TIMEZONE_COOKIE_NAME, form.cleaned_data['timezone'])

        return super(CurrentUserLocaleProfileEditView, self).form_valid(form)

    def get_object(self):
        return self.request.user.locale_profile


class HomeView(TemplateView):
    template_name = 'appearance/home.html'

    def get_context_data(self, **kwargs):
        data = super(HomeView, self).get_context_data(**kwargs)
        data.update({
            'hide_links': True,
            'search_results_limit': 100,
            'search_terms': self.request.GET.get('q'),
            'missing_list': [item for item in MissingItem.get_all() if item.condition()],
        })
        return data

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        queryset, ids, timedelta = document_search.search(request.GET, request.user)

        # Update the context with the search results
        context.update({
            'object_list': queryset,
            'time_delta': timedelta,
            'title': _('Results'),
        })

        return self.render_to_response(context)


class LicenseView(SimpleView):
    extra_context = {
        'form': LicenseForm(),
        'read_only': True,
        'title': _('License'),
    }
    template_name = 'appearance/generic_form.html'


class SetupListView(TemplateView):
    template_name = 'appearance/generic_list_horizontal.html'

    def get_context_data(self, **kwargs):
        data = super(SetupListView, self).get_context_data(**kwargs)
        data.update({
            'resolved_links': menu_setup.resolve(context=RequestContext(self.request)),
            'title': _('Setup items'),
        })
        return data


class ToolsListView(SimpleView):
    template_name = 'appearance/generic_list_horizontal.html'

    def get_menu_links(self):
        return menu_tools.resolve(context=RequestContext(self.request))

    def get_extra_context(self):
        return {
            'resolved_links': self.get_menu_links(),
            'title': _('Tools'),
        }


def multi_object_action_view(request):
    """
    Proxy view called first when using a multi object action, which
    then redirects to the appropiate specialized view
    """

    next = request.POST.get('next', request.GET.get('next', request.META.get('HTTP_REFERER', reverse(settings.LOGIN_REDIRECT_URL))))

    action = request.GET.get('action', None)
    id_list = ','.join([key[3:] for key in request.GET.keys() if key.startswith('pk_')])
    items_property_list = [loads(key[11:]) for key in request.GET.keys() if key.startswith('properties_')]

    if not action:
        messages.error(request, _('No action selected.'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse(settings.LOGIN_REDIRECT_URL)))

    if not id_list and not items_property_list:
        messages.error(request, _('Must select at least one item.'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse(settings.LOGIN_REDIRECT_URL)))

    # Separate redirects to keep backwards compatibility with older
    # functions that don't expect a properties_list parameter
    if items_property_list:
        return HttpResponseRedirect('%s?%s' % (
            action,
            urlencode({'items_property_list': dumps(items_property_list), 'next': next}))
        )
    else:
        return HttpResponseRedirect('%s?%s' % (
            action,
            urlencode({'id_list': id_list, 'next': next}))
        )
