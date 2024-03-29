/* App Module */
var geniframework = angular.module('geniframework', []);

geniframework.config(['$routeProvider', function($routeProvider){
	$routeProvider.when('/home', {
		templateUrl : '../../static/partials/home.html',
		controller : HomeController
	});
    $routeProvider.when('/unique', {
		templateUrl : '../../static/partials/unique.html',
		controller : UniqueController
	});
	$routeProvider.otherwise({
    	redirectTo : '/unique'
	});
}]);

function HomeController($scope,$rootScope, $http){
    var httpPromise = $http;
    var profileAPI = '/getProfile';
    $scope.loading = true;
    callServerGETAPI(httpPromise, profileAPI, procesSearch);

    $scope.recentProfiles = [];

    function procesSearch(responseData){
        $scope.loading = false;
        $('.loadingMask').hide();
        $scope.profileData = responseData;
        $scope.profileId = $scope.profileData.id;
        $scope.profileName = $scope.profileData.name;
    }

    $scope.getProfile = function(id, name){
        var profileAPI = 'js/json/' + id+'.js';
        $scope.loading = true;
        $('.loadingMask').show();
        callServerGETAPI(httpPromise, profileAPI, procesSearch);
        if($scope.recentProfiles.length === 0){
            var profileObj = {"id" : $scope.profileId, "name" : $scope.profileName}
            $scope.recentProfiles.push(profileObj);
        }else{
          var count = 0;
            var profileObj = {"id" : $scope.profileId, "name" : $scope.profileName};
            $.each($scope.recentProfiles, function(index, value) {
                //console.log(JSON.stringify($scope.recentProfiles));
                //console.log(value.id + "------" + id);
              if(value.id === $scope.profileId){
				 count = count + 1;
			  }
		   });
            if(count === 0){
                $scope.recentProfiles.push(profileObj);
            }
        }
    }
}

var UniqueController = function($scope, $rootScope, $http){
    var httpPromise = $http;
    $('#uniqueProfilesTab a[href="#profile"]').tab('show');
    $scope.showTableDataMyProfile = false;
    $scope.showTableDataOtherProfile = false;
    $scope.showTableDataMyPresidents = false;
		$scope.clearTargetProfile = function($event){
			$scope.myProjectsForm.sourceProfile = "";
			$scope.myProjects2Form.sourceProfile = "";
		};

		$scope.checkMyProjectsFormValid = function() {
			var result = !($scope.myProjectsForm.$valid || (!$scope.myProjectsForm.checked && $scope.myProjectsForm.email.$valid && typeof $scope.myProjectsForm.project_id !== 'undefined'));
			return result;
		}
		$scope.checkMyProjects2FormValid = function() {
			var result = !($scope.myProjects2Form.$valid || (!$scope.myProjects2Form.checked && $scope.myProjects2Form.email.$valid && typeof $scope.myProjects2Form.project_id.$valid));
			return result;
		}
    $scope.submitMyProfile = function(formId){
        var getFormData = $(formId).serialize();
        $rootScope.formId = formId;
        switch($rootScope.formId) {
					case '#myProfileForm':
        		var submiProfileAPI = '/getPath2User?'+getFormData;
	          if($scope.myProfileForm.$valid){
	              $scope.loading = true;
	              $('.loadingMask').show();
	              callServerGETAPI(httpPromise, submiProfileAPI, showTableData);
	          }
						break;
        	case '#otherProfileForm':
	        	//Other form
		        var submiProfileAPI = '/getPath2User?'+getFormData;
	          if($scope.otherProfileForm.$valid){
	              $scope.loading = true;
	              $('.loadingMask').show();
	              callServerGETAPI(httpPromise, submiProfileAPI, showTableData);
	          }
					case '#myProjectsForm':
        		var submiProfileAPI = '/getPath2Projects?'+getFormData;
	          if(!$scope.checkMyProjectsFormValid()){
	              $scope.loading = true;
	              $('.loadingMask').show();
	              callServerGETAPI(httpPromise, submiProfileAPI, showTableData);
	          }
						break;
					case '#myProjects2Form':
        		var submiProfileAPI = '/getPath2Projects?'+getFormData;
	          if(!$scope.checkMyProjects2FormValid()){
	              $scope.loading = true;
	              $('.loadingMask').show();
	              callServerGETAPI(httpPromise, submiProfileAPI, showTableData);
	          }
						break;
        }
    }

    function showTableData(responseData){
        $scope.loading = false;
        $('.loadingMask').hide();
        switch($rootScope.formId) {
					case '#otherProfileForm':
            $scope.otherProfileData = responseData;
            if(! angular.isUndefined($scope.otherProfileData.backgroundMessage)){
                $scope.otherProfileFormSuccessMsg = true;
                $('#otherProfileFormSuccessMsg').html($scope.otherProfileData.backgroundMessage);
                $('#otherProfileFormSuccessMsg').css("background-color","#00BFFF");
                setTimeout(function(){
                    $scope.otherProfileFormSuccessMsg = false;
                    $('#otherProfileFormSuccessMsg').fadeOut('slow');
                }, 5000);
            };
            $scope.showTableDataOtherProfile = true;
            $scope.otherProfileForm.emailField = null;
						break;
        	case '#myProfileForm':
            $scope.myProfileData = responseData;
            console.log(!angular.isUndefined($scope.myProfileData.backgroundMessage));
            if(!angular.isUndefined($scope.myProfileData.backgroundMessage)){
                $scope.myProfileFormSuccessMsg = true;
                $('#myProfileFormSuccessMsg').html($scope.myProfileData.backgroundMessage);
                $('#myProfileFormSuccessMsg').css("background-color","#00BFFF");
                setTimeout(function(){
                    $scope.myProfileFormSuccessMsg = false;
                    $('#myProfileFormSuccessMsg').fadeOut('slow');
                }, 5000);
            };
            $scope.showTableDataMyProfile = true;
            $scope.myProfileForm.emailField = null;
						break;
        	case '#myProjectsForm':
            $scope.myProjectsData = responseData;
            console.log(!angular.isUndefined($scope.myProjectsData.backgroundMessage));
            if(!angular.isUndefined($scope.myProjectsData.backgroundMessage)){
                $scope.myProjectsFormSuccessMsg = true;
                $('#myProjectsFormSuccessMsg').html($scope.myProjectsData.backgroundMessage);
                $('#myProjectsFormSuccessMsg').css("background-color","#00BFFF");
                setTimeout(function(){
                    $scope.myProjectsFormSuccessMsg = false;
                    $('#myProjectsFormSuccessMsg').fadeOut('slow');
                }, 5000);
            };
            $scope.showTableDataMyProjects = true;
            $scope.myProjectsForm.emailField = null;
						break;
        	case '#myProjects2Form':
            $scope.myProjects2Data = responseData;
            console.log(!angular.isUndefined($scope.myProjects2Data.backgroundMessage));
            if(!angular.isUndefined($scope.myProjects2Data.backgroundMessage)){
                $scope.myProjects2FormSuccessMsg = true;
                $('#myProjects2FormSuccessMsg').html($scope.myProjects2Data.backgroundMessage);
                $('#myProjects2FormSuccessMsg').css("background-color","#00BFFF");
                setTimeout(function(){
                    $scope.myProjects2FormSuccessMsg = false;
                    $('#myProjects2FormSuccessMsg').fadeOut('slow');
                }, 5000);
            };
            $scope.showTableDataMyProjects2 = true;
            $scope.myProjects2Form.emailField = null;
						break;
        }
    }

};


function callServerGETAPI(httpPromise, apiName, reponseHandler){
	httpPromise.get(apiName).success(reponseHandler);
}
