angular.module( 'wikiaAuthority.wiki_users', [
  'ui.router',
  'wikiaAuthority.wiki'
])

/**
 * Each section or module of the site can also have its own routes. AngularJS
 * will handle ensuring they are all available at run-time, but splitting it
 * this way makes each module more "self-contained".
 */
.config(function config( $stateProvider ) {
  $stateProvider.state( 'wiki_users', {
    url: '/wiki/:wiki_id/users',
    views: {
      "main": {
        controller: 'WikiUsersCtrl',
        templateUrl: 'wiki_users/wiki_users.tpl.html'
      }
    },
    data:{ pageTitle: 'Users for Wiki' }
  });
})
.service( 'WikiUsersService', ['WikiService', function WikiUsersService(WikiService) {

}]

)
/**
 * And of course we define a controller for our route.
 */
.controller( 'WikiUsersCtrl', function WikiUsersController( $scope ) {
})

;

