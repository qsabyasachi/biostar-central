from django import template
import urllib, hashlib
from datetime import datetime, timedelta
from main.server import const

register = template.Library()

@register.inclusion_tag('widgets/comments.html', takes_context=True)
def comments(context, post):
    return {'post':post, 'permissions':context['permissions']}

@register.inclusion_tag('widgets/userlink.html')
def userlink(user):
    return {'user':user}
    
@register.inclusion_tag('widgets/taglink.html')
def taglink(tag_name):
    return {'tag_name':tag_name}

@register.inclusion_tag('widgets/userrep.html')
def userrep(user):
    return {'user':user}
    
@register.inclusion_tag('widgets/badgeicon.html')
def badgeicon(type):
    return {'type':type}

@register.inclusion_tag('widgets/actionbox.html')
def actionbox(user, date, action='asked'):
    return {'user':user, 'date':date, 'action':action}
    
@register.inclusion_tag('widgets/userbox.html')
def userbox(user):
    return {'user':user}
    
@register.inclusion_tag('widgets/revisionbox.html')
def revisionbox(post):
    return {'post':post}

@register.simple_tag
def time_ago(time):
    delta = datetime.now() - time
    if delta < timedelta(minutes=1):
        return 'just now'
    if delta < timedelta(hours=1):
        return '%d min ago' % (delta.seconds // 60 )
    if delta < timedelta(days=1):
        return '%d hrs ago' % (delta.seconds // 3600 )
    if delta < timedelta(days=30):
        return '%d days ago' % delta.days
    return time.strftime('%b %d at %H:%M')

@register.simple_tag
def gravatar(user, size=80):
    gravatar_url = "http://www.gravatar.com/avatar.php?"
    gravatar_url += urllib.urlencode({
        'gravatar_id':hashlib.md5(user.email).hexdigest(),
        'size':str(size)})
    return """<img src="%s" alt="gravatar for %s"/>""" % (gravatar_url, user.username)

@register.inclusion_tag('widgets/pagebar.html', takes_context=True)
def pagebar(context):
    return {
        'page': context['page'],
        'search': context.get('search',''),
        'request': context['request'],
    }
    
@register.inclusion_tag('widgets/question-list-narrow.html')
def question_list_narrow(x):
    return {'posts':x}

@register.inclusion_tag('widgets/answer-list-narrow.html')
def answer_list_narrow(x):
    return {'answers':x}
    
@register.simple_tag(takes_context=True)
def navclass(context, include_path, exclude_paths=''):
    path = context['request'].get_full_path()
    if include_path in path:
        if not exclude_paths or (True not in [pat in path for pat in exclude_paths.split(' ')]):
            return 'class="youarehere"'
    return ''
    
@register.simple_tag
def bignum(number):
    "Reformats numbers with qualifiers as K, M, G"
    try:
        value = float(number)/1000.0        
        if value > 1:
            return "%0.1fk" % value
    except ValueError, exc:
        pass
    return str(number)
    
@register.simple_tag
def designation(user):
    "Renders a designation for the user"
    if user.profile.is_admin:
        return 'Administrator'
    elif user.profile.is_moderator:
        return 'Moderator'
    return "Registered user"
    
@register.simple_tag
def flair(user):
    "Renders a designation for the user"
    if user.profile.is_admin:
        return '&diams;&diams;'
    elif user.profile.is_moderator:
        return '&diams;'
    return ""