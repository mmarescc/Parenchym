/**
 * bootstraps angular onto the window.document node
 */

define(['ng', 'pym/app'], function (angular) {
    'use strict';

    require(['requirejs/domReady!'], function (document) {
        angular.bootstrap(document, ['PymApp']);
    });
});
