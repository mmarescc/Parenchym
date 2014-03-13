<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">Authentication Manager</%block>
<%block name="styles">
${parent.styles()}
</%block>

<div class="outer-gutter">

<ul>
    <li><a href="${request.resource_url(request.context['principal'])}">Manage Principals</a></li>
    <li><a href="${request.resource_url(request.context['role'])}">Manage Roles</a></li>
    <li><a href="${request.resource_url(request.context['rolemember'])}">Manage Rolemembers</a></li>
</ul>

</div>