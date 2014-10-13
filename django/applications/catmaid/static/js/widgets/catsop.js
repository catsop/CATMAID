"use strict";

var CatsopWidget = function () {
	this.widgetID = this.registerInstance();
};

CatsopWidget.prototype = {};
$.extend(CatsopWidget.prototype, new InstanceRegistry());

CatsopWidget.prototype.init = function () {

};