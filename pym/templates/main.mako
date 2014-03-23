<%inherit file="pym:templates/_layouts/default.mako" />
<%block name="meta_title">Welcome</%block>
<%block name="styles">
${parent.styles()}
</%block>

<div class="row">
    <div class="col-md-offset-8 col-md-4">
        <p><a href="${request.resource_url(request.root['__sys__'])}">System</a></p>
        <ul>
            <li><a href="${request.resource_url(request.root['__sys__']['authmgr'])}">Authentication Manager</a>
                <ul>
                    <li><a href="${request.resource_url(request.root['__sys__']['authmgr']['user'])}">Manage Users</a></li>
                    <li><a href="${request.resource_url(request.root['__sys__']['authmgr']['group'])}">Manage Groups</a></li>
                    <li><a href="${request.resource_url(request.root['__sys__']['authmgr']['group_member'])}">Manage Group Members</a></li>
                </ul>
            </li>
        </ul>
    </div>
</div>


<div class="outer-gutter">

    <p>M.A.I.N.</p>

</div>
