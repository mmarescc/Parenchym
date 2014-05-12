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
            <!--link rel="stylesheet" href="${request.static_url('pym:static/vendor/jquery-ui-themes/themes/ui-lightness/jquery-ui.min.css')}"-->
            <link rel="stylesheet" href="${request.static_url('pym:static/vendor/pnotify/pnotify.custom.min.css')}">
            <link rel="stylesheet" href="${request.static_url('pym:static/css/styles2.css')}">
            % if request.registry.settings['environment'] != 'production':
                <link rel="stylesheet" href="${request.static_url('pym:static/css/styles-' + request.registry.settings['environment'] + '.css')}">
            % endif
        </%block>
        <script>
        <%block name="require_config">
            var PYM_APP_REQUIREMENTS = ['ng'];
            var PYM_APP_INJECTS = [];
            var require = {
                  baseUrl: '${request.resource_url(request.root)}'
                , deps: [
                    '${request.static_url('pym:static/app/plugins.js')}',
                    //'${request.static_url('pym:static/vendor/deform/js/deform.js')}',
                    '${request.static_url('pym:static/app/boot-ng.js')}'
                ]
                , paths: {
                      'jquery':          'static-pym/vendor/jquery/dist/jquery.min'
                    , 'jq-ui':           'static-pym/vendor/jquery-ui/ui/minified/jquery-ui.min'
                    , 'requirejs':       'static-pym/vendor/requirejs'
                    , 'd3':              'static-pym/vendor/d3/d3.min'
                    , 'pnotify':         'static-pym/vendor/pnotify/pnotify.core'
                    , 'pnotify.buttons': 'static-pym/vendor/pnotify/pnotify.buttons'
                    , 'select2':         'static-pym/vendor/select2/select2.min'
                    , 'ng':              'static-pym/vendor/angular/angular.min'
                    , 'ng-resource':     'static-pym/vendor/angular-resource/angular-resource.min'
                    , 'ng-grid':         'static-pym/vendor/angular-grid/build/ng-grid.min'
                    , 'ng-ui':           'static-pym/vendor/angular-ui/build/angular-ui.min'
                    , 'ng-ui-select2':   'static-pym/vendor/angular-ui-select2/src/select2'
                    , 'ng-ui-bs':        'static-pym/vendor/angular-ui-bootstrap'
                    , 'ng-ui-router':    'static-pym/vendor/angular-ui-router/release/angular-ui-router.min'
                    , 'pym':             'static-pym/app'
                    , 'pym-v':           'static-pym/vendor'
                    , 'ccg':             'static-ccg/app'
                    , 'ccg-v':           'static-ccg/vendor'
                }
                , shim: {
                      'jq-ui':                                ['jquery']
                    , 'select2':                              ['ng']
                    , 'pnotify.buttons':                      ['pnotify']
                    , 'ng':                                   {deps: ['jquery'], exports: 'angular'}
                    , 'ng-resource':                          ['ng']
                    , 'ng-grid':                              ['ng']
                    , 'ng-ui':                                ['ng']
                    , 'ng-ui-select2':                        ['ng', 'select2']
                    , 'ng-ui-bs':                             ['ng']
                    , 'ng-ui-router':                         ['ng']
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
        require(['requirejs/domReady!', 'jquery', 'pym/pym', 'ng',    'pym/app'],
        function( doc,                   $,        PYM,       angular, PymApp) {
            ${pym.growl_flash()}

            var MainMenuCtrl = PymApp.controller('MainMenuCtrl',
                    ['$scope', '$http',
            function ($scope, $http) {

                $scope.model = {};
                $scope.model.items = {};
                $scope.model.active_item = null;

                function load_menu_items()
                {
                    $http.get('/xhr_main_menu', {})
                        .success(function(data, status, headers, config) {
                            $scope.model.items = data.data;
                        });
                }
                load_menu_items();

            }]);

        });
        </script>
    </body>
</html>
