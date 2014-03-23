<%namespace name="pym" file="pym:templates/_lib/pym.mako" inheritable="True"/>

<!DOCTYPE html>
<html class="no-js">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
        <meta name="viewport" content="width=device-width">
          <title><%block name="meta_title">${request.registry.settings['project.title']}
            % if 'project.subtitle' in request.registry.settings:
                <small>${request.registry.settings['project.subtitle']}</small>
            % endif
        </%block></title>
        <meta name="description" content="<%block name="meta_descr">${request.registry.settings['project.description']}</%block>">
        <meta name="keywords"    content="<%block name="meta_keywords">${request.registry.settings['project.keywords']}</%block>">
        <meta name="author"      content="<%block name="meta_author">${request.registry.settings['project.author']}</%block>">
        <%block name="styles">
            <link rel="stylesheet" href="${request.static_url('pym:static/css/styles.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/vendor/jquery/ui/themes/ui-lightness/jquery-ui.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/vendor/jquery/ui/timepicker/timepicker.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/vendor/jquery/ui/pnotify/jquery.pnotify.default.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/vendor/deform/css/form.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/css/styles2.css')}">
            % if request.registry.settings['environment'] != 'production':
                <link rel="stylesheet" href="${request.static_url('pym:static/css/styles-' + request.registry.settings['environment'] + '.css')}">
            % endif
        </%block>
        <script>
        <%block name="require_config">
            var PYM_APP_REQUIREMENTS = ['ng/angular.min'];
            var PYM_APP_INJECTS = [];
            var require = {
                  baseUrl: '${request.resource_url(request.root)}'
                , deps: [
                    '${request.static_url('pym:static/app/plugins.js')}',
                    //'${request.static_url('pym:static/vendor/deform/js/deform.js')}',
                    '${request.static_url('pym:static/app/boot-ng.js')}',
                ]
                , paths: {
                      'jquery':    'static-pym/vendor/jquery/jquery'
                    , 'ui':        'static-pym/vendor/jquery/ui'
                    , 'ng':        'static-pym/vendor/angular'
                    , 'requirejs': 'static-pym/vendor/requirejs'
                    , 'pym':       'static-pym/app'
                }
                , shim: {
                      'static-pym/vendor/jstorage':               ['jquery']
                    , 'static-pym/vendor/tinymce/jquery.tinymce': ['jquery']
                    , 'ui/jquery-ui':                             ['jquery']
                    , 'ui/timepicker/timepicker':           ['ui/jquery-ui']
                    , 'ui/pnotify/jquery.pnotify':          ['ui/jquery-ui']
                    , 'ng/angular.min':                           {deps: ['jquery'], exports: 'angular'}
                    , 'ng/ui/ui-bootstrap-tpls-0.10.0.min': ['ng/angular.min']
                    , 'ng/ng-grid/ng-grid.min':             ['ng/angular.min']
                }
                , waitSeconds: 15
            };
        </%block>
        </script>
        <%block name="scripts">
            <script src="${request.static_url('pym:static/vendor/requirejs/require.min.js')}"></script>
            <script>
            require(['pym/pym'], function(PYM) {
                PYM.init({
                    csrf_token: '${request.session.get_csrf_token()}'
                });
                //deform.load();
            });
            </script>
        </%block>
    </head>
    <body>
        <!--[if lt IE 7]>
            <p class="chromeframe">You are using an outdated browser. <a href="http://browsehappy.com/">Upgrade your browser today</a> or <a href="http://www.google.com/chromeframe/?redirect=true">install Google Chrome Frame</a> to better experience this site.</p>
        <![endif]-->

        <div id="page_container"><!-- BEGIN #page_container -->

            <%include file="pym:templates/_layouts/page_header.mako" args="parent=self, pym=pym, render_flash=False" />

            <div id="page_content"><!-- BEGIN #page_content -->
                  ${next.body()}
            </div><!-- END #page_content -->

        </div><!-- END #page_container -->

            <%include file="pym:templates/_layouts/page_footer.mako" />
        <script>
        require(['requirejs/domReady!', 'jquery', 'pym/pym'], function(doc, $, PYM) {
            ${pym.growl_flash()}
        });
        </script>
    </body>
</html>
