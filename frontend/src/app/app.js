angular.module( 'wikiaAuthority', [
  'templates-app',
  'templates-common',
  'wikiaAuthority.home',
  'wikiaAuthority.hubs',
  'wikiaAuthority.topic',
  'wikiaAuthority.topic_pages',
  'wikiaAuthority.topic_users',
  'wikiaAuthority.topic_wikis',
  'wikiaAuthority.user',
  'wikiaAuthority.user_pages',
  'wikiaAuthority.user_topics',
  'wikiaAuthority.user_wikis',
  'wikiaAuthority.wiki',
  'wikiaAuthority.wiki_pages',
  'wikiaAuthority.wiki_users',
  'wikiaAuthority.wiki_topics',
  'ui.router'
])

.config( function myAppConfig ( $stateProvider, $urlRouterProvider ) {
  $urlRouterProvider.otherwise( '/home' );
})

.run( function run () {
})

.controller( 'AppCtrl', function AppCtrl ( $scope, $location ) {
  $scope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams){
    if ( angular.isDefined( toState.data.pageTitle ) ) {
      $scope.pageTitle = toState.data.pageTitle + ' | WikiaAuthority' ;
    }
  });
})

;

