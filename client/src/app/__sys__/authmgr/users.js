require(['requirejs/domReady!', 'ng',     'pym/app', 'ng-resource', 'ng-ui-router'],
function (document,              angular,  PymApp) {

    'use strict';

    var sys_authmgr_users = angular.module('sys_authmgr_users', ['ui.router', 'ngGrid', 'PymApp', 'ngResource'])

        .config(
                ['$stateProvider', '$urlRouterProvider',
        function ($stateProvider,   $urlRouterProvider) {

            $urlRouterProvider.otherwise('/entity');

            $stateProvider
                .state('browse', {
                    url: '/entity',
                    templateUrl: 'browse.html',
                    controller: 'BrowseCtrl'
                })
                .state('view', {
                    url: '/entity/{entity_id:[0-9]{1,}}',
                    templateUrl: 'view.html',
                    controller: 'ViewCtrl'
                });
        }])

        // TODO Inject settings of filter, paging, sorting
        .factory('Entities', ['$resource', 'URLS', function ($resource, URLS) {
            var url = URLS['entity_rest_url'] + '/:id';
            return $resource(url, {}, {
                update: {method:'PUT'}
            });
        }])

        .controller('BrowseCtrl',
                ['$scope', '$state',
        function ($scope,   $state) {
            $scope.goto_view = function () {
                if (! angular.isDefined($scope.crud_grid.selected[0])) {
                    alert('Please select a row first.');
                    return;
                }
                $state.go('view', {entity_id: $scope.crud_grid.selected[0].id});
            };
        }])

        .controller('ViewCtrl',
                ['$scope', '$state', '$stateParams', 'Entities',
        function ($scope,   $state,   $stateParams, Entities) {
            $scope.entity_id = $stateParams.entity_id;
            $scope.state = $state;
            Entities.get({id: $scope.entity_id}, function(entity){
                $scope.entity = entity;
            });
        }]);

    return sys_authmgr_users;
});