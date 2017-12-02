import logging
import shutil
import uuid

import hjson
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.template import loader
from django.test.client import RequestFactory
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.template import Template, Context
from django.conf import settings

from biostar.accounts.models import Profile
from . import factory
from .const import *
from .models import Data, Analysis, Job, Project, Access

CHUNK = 1024 * 1024

logger = logging.getLogger("engine")


def get_uuid(limit=32):
    return str(uuid.uuid4())[:limit]


def join(*args):
    return os.path.abspath(os.path.join(*args))


def get_analysis_attr(analysis, project=None):
    "Get analysis attributes"

    project = project or analysis.project
    json_text = analysis.json_text
    template = analysis.template
    owner = analysis.owner
    summary = analysis.summary
    name = analysis.name
    text = analysis.text

    return dict(project=project, json_text=json_text, template=template,
                user=owner, summary=summary, name=name, text=text, )


def generate_script(job):
    """
    Generates a script from a job.
    """
    work_dir = job.path
    json_data = hjson.loads(job.json_text)

    # The base url to the site.
    url_base = f'{settings.PROTOCOL}://{settings.SITE_DOMAIN}{settings.HTTP_PORT}'

    # Extra context added to the script.
    runtime = dict(
        media_root=settings.MEDIA_ROOT,
        media_url=settings.MEDIA_URL,
        work_dir=work_dir, local_root=settings.LOCAL_ROOT,
        user_id=job.owner.id, user_email=job.owner.email,
        job_id=job.id, job_name=job.name,
        job_url=f'{url_base}{settings.MEDIA_URL}{job.get_url()}'.rstrip("/"),
        project_id=job.project.id, project_name=job.project.name,
        analyis_name=job.analysis.name,
        analysis_id=job.analysis.id,
        domain=settings.SITE_DOMAIN, protocol=settings.PROTOCOL,
    )

    # Add the runtime context to the data.
    json_data['runtime'] = runtime

    # Generate the script.
    template = Template(job.template)
    context = Context(json_data)
    script = template.render(context)

    return json_data, script


def get_project_list(user):
    """
    Return projects visible to a user.
    """

    if user.is_anonymous:
        # Unauthenticated users see public projects.
        cond = Q(privacy=Project.PUBLIC)
    else:
        # Authenticated users see public projects and private projects with access rights.
        cond = Q(privacy=Project.PUBLIC) | Q(access__user=user, access__access__gt=Access.NO_ACCESS)

    # Generate the query.
    query = Project.objects.filter(cond)

    return query


def access_fields(users, project):

    access_fields = []

    for user in users:
        initial = Access.objects.filter(user=user, project=project).first()

        if not initial:
            initial = Access(access=Access.NO_ACCESS)

        # Unique field name using users uid
        unique_name = Profile.objects.filter(user=user).first().uid
        label = user.first_name

        access = forms.IntegerField(widget=forms.Select(choices=Access.ACCESS_CHOICES),
                                    initial=initial.access, label=label)
        access_fields.append((unique_name, access))

    return access_fields


def check_obj_access(user, instance, access=Access.ADMIN_ACCESS, request=None, login_required=False):
    """
    Validates object access.
    """
    # This is so that we can inform users in more granularity
    # but also to allow this function to be called outside a web view
    # where there are no requests.
    request = request or RequestFactory()

    # The object does not exist.
    if not instance:
        messages.error(request, "Object not found!")
        return False

    # A textual representation of the access
    access_text = Access.ACCESS_MAP.get(access, 'Invalid')

    # Works for projects or objects with an attribute of project.
    if hasattr(instance, "project"):
        project = instance.project
    else:
        project = instance

    # Check for logged in user and login requirement.
    if user.is_anonymous() and login_required:
        msg = f"""
            You must be logged in to perform that action.
        """
        msg = mark_safe(msg)
        messages.error(request, msg)
        return False

    # If the project is public or shareable project and a user is asking for read access.
    if (project.privacy in (Project.PUBLIC, Project.SHAREABLE)):
        if (access in (Access.READ_ACCESS, Access.RECIPE_ACCESS)):
            return True

    # Anonymous users have no other access permissions.
    if user.is_anonymous():
        msg = f"""
        You must be logged in and have <span class="ui green label">{access_text}</span> to perform that action.
        """
        msg = mark_safe(msg)
        messages.error(request, msg)
        return False

    deny = f"""
        Access Denied. This action requires <span class="ui green label">{access_text}</span>.
        """
    deny = mark_safe(deny)

    # Check user access.
    entry = Access.objects.filter(user=user, project=project).first()

    # No access permissions for the user on the project.
    if not entry:
        messages.error(request, deny)
        return False

    # The stored access is less than the required access.
    if entry.access < access:
        messages.warning(request, deny)
        return False

    # Permissions granted to the object.
    if entry.access >= access:
        return True

    # This should never trigger and is here to catch bugs.
    messages.error(request, "Access denied! Invalid fall-through!")
    return False


def get_data(user, project, query, data_type=None):
    """
    Returns a dictionary keyed by data stored in the project.
    """
    if data_type:
        query = query.filter(data_type=data_type)
    datamap = dict((obj.id, obj) for obj in query)
    logger.info(f"{user.email} got {len(datamap)} data from {project.name}")

    return datamap


def create_project(user, name, uid='', summary='', text='', stream='',
                   privacy=Project.PRIVATE, sticky=True):
    project = Project.objects.create(
        name=name, uid=uid, summary=summary, text=text, owner=user, privacy=privacy, sticky=sticky)

    if stream:
        project.image.save(stream.name, stream, save=True)

    logger.info(f"Created project: {project.name} uid: {project.uid}")

    return project


def create_analysis(project, json_text, template, uid=None, user=None, summary='', name='', text=''):
    owner = user or project.owner
    name = name or 'Analysis name'
    text = text or 'Analysis text'

    analysis = Analysis.objects.create(project=project, uid=uid, summary=summary, json_text=json_text,
                                       owner=owner, name=name, text=text,
                                       template=template)

    logger.info(f"Created analysis: uid={analysis.uid} name={analysis.name}")

    return analysis


def make_summary(data, summary='', name="widgets/job_summary.html"):
    '''
    Summarizes job parameters.
    '''

    context = dict(data=data, summary=summary)
    template = loader.get_template(name)
    result = template.render(context)
    return result


def create_job(analysis, user=None, json_text='', json_data={}, name=None, state=None, save=True):
    name = name or analysis.name
    state = state or Job.QUEUED
    owner = user or analysis.project.owner

    project = analysis.project

    if json_data:
        json_text = hjson.dumps(json_data)
    else:
        json_text = json_text or analysis.json_text

    # Needs the json_data to set the summary.
    json_data = hjson.loads(json_text)

    # Generate the summary from the data.
    summary = make_summary(json_data, summary=analysis.summary)

    # Create the job instance.
    job = Job(name=name, summary=summary, state=state, json_text=json_text,
                             project=project, analysis=analysis, owner=owner,
                             template=analysis.template)
    if save:
        logger.info(f"Created job: {job.name}")
        job.save()

    return job


def findfiles(location, collect):
    """
    Returns a list of all files in a directory.
    """
    for item in os.scandir(location):
        if item.is_dir():
            findfiles(item.path, collect=collect)
        else:
            collect.append(os.path.abspath(item.path))
    return collect


def create_data_path(data, fname):
    # Limit the file name lenght.
    fname = os.path.basename(fname)[-100:]

    # Slugify each element of the path to make them "safe".
    pieces = map(slugify, fname.split("."))

    # Put it back together.
    fname = ".".join(pieces)

    # This will store the data.
    data_dir = data.get_data_dir()

    # Make the data directory if it does not exist.
    os.makedirs(data_dir, exist_ok=True)

    # Build file with original name.
    data_path = os.path.join(data_dir, fname)

    return data_path


def create_data(project, user=None, stream=None, path='', name='',
                text='', summary='', data_type=None, link=False):
    # Absolute paths with no trailing slashes.
    path = os.path.abspath(path).rstrip("/")

    # Create the data.
    state = Data.PENDING
    data = Data.objects.create(name=name, owner=user, state=state, project=project,
                               data_type=data_type, summary=summary, text=text)

    # If the path is a directory, symlink all files.
    if path != os.path.abspath("") and os.path.isdir(path):

        logger.info(f"Symlinking path: {path}")
        collect = findfiles(path, collect=[])
        for src in collect:
            dest = create_data_path(data, src)
            os.symlink(src, dest)
        summary = f'Contains {len(collect)} files. {summary}'
        logger.info(f"Symlinked {len(collect)} files.")

    # The path is a file.
    if path != os.path.abspath("") and os.path.isfile(path):

        dest = create_data_path(data, path)

        # Test if it should be linked or not.
        if link:
            os.symlink(path, dest)
            logger.info(f"Symlinked file: {path}")
        else:
            logger.info(f"Copied file to: {dest}")
            shutil.copy(path, dest)

    # An incoming stream is written into the destination.
    if stream:
        dest = create_data_path(data, stream.name)
        with open(dest, 'wb') as fp:
            chunk = stream.read(CHUNK)
            while chunk:
                fp.write(chunk)
                chunk = stream.read(CHUNK)

    # Invalid paths and empty streams still create the data.
    missing = not (os.path.isdir(path) or os.path.isfile(path) or stream)
    if path and missing:
        state = Data.ERROR
        logger.error(f"Path not found for: {path}")
    else:
        state = Data.READY

    # Find all files in the data directory.
    collect = findfiles(data.get_data_dir(), collect=[])

    # Remove the table of contents from the collected files.
    collect.remove(data.get_path())

    # Write the table of contents.
    with open(data.file, 'w') as fp:
        fp.write("\n".join(collect))

    size = 0
    for elem in collect:
        if os.path.isfile(elem):
            size += os.stat(elem, follow_symlinks=True).st_size

    # Finalize the data.
    name = name or os.path.split(path)[1] or 'data.bin'
    Data.objects.filter(pk=data.pk).update(size=size, state=state, name=name, summary=summary)

    # Refresh the data information that is held by the reference.
    data = Data.objects.get(pk=data.pk)

    # Report the data creation.
    logger.info(f"Added data id={data.pk}, type={data.data_type} name={data.name}")

    return data
