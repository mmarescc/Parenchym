<%!
    from pprint import pformat
%>

<%block name="pageFooter">
    <footer class="hidden-print">
        <div class="row">
            <div class="col-md-2">
                ${request.registry.settings['project.title']} ${request.registry.settings['project.version']}
            </div>
            <div class="col-md-10" style="text-align: right;">
                <div style="display: inline-block; margin-right: 2em;"><a href="${request.registry.settings['project.copyright_link']}" target="_blank">${request.registry.settings['project.copyright']|n}</a></div>
                <div style="display: inline-block;"><a href="${request.resource_url(request.root, 'imprint')}">Imprint</a></div>
            </div>
        </div>
    </footer>
</%block>

% if request.registry.settings['debug']:
    <hr>
    <h3>SESSION</h3>
    <table class="tblLayout">
        <tbody>
            % for k, v in request.session.items():
                <tr style="border-bottom: solid 1px silver;">
                    <td style="vertical-align: top;">${k}</td><td style="white-space:pre;">${pformat(v)}</td>
                </tr>
            % endfor
        </tbody>
    </table>
    <h3>Context ACL</h3>
    <table class="tblLayout">
        <tbody>
            % for ace in request.context.__acl__:
                <tr>
                    % for x in ace:
                        <td style="border: solid 1px silver; padding: 2px 4px;">${x}</td>
                    % endfor
                </tr>
            % endfor
        </tbody>
    </table>
    ## Bust footer
    <p style="margin-top: 8ex;">&nbsp;</p>
% endif
