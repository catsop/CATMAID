
/**
 AreaServerModel singleton class abstracts area persistence
 */
var AreaServerModel = new function()
{
    var areaTools = [];
    var django_url = '/sopnet/';

    /**
     Push a new trace (ie, fabricjs object) to the backend.
     */
    this.pushTrace = function(stack, brushWidth, assemblyId, objectContainer, callback)
    {
        var x = [];
        var y = [];
        var pts = [];
        var obj = objectContainer.obj;
        var project = stack.getProject();
        var view_top = stack.screenPosition().top;
        var view_left = stack.screenPosition().left;
        var scale = stack.scale;
        var url = '/user_slice';
        var bound_rect = obj.getBoundingRect();
        var o_left = (bound_rect.left + (brushWidth / 2.0)) / scale + view_left;
        var o_top = (bound_rect.top + (brushWidth / 2.0)) / scale + view_top;
        var r = brushWidth / (2.0 * scale);

        /*console.log('o_left: ' + o_left + ', o_top: ' + o_top);
        console.log('o_left_c: ' + obj.left + ', o_top_c: ' + obj.top);*/


        for (var i = 0; i < obj.path.length; ++i)
        {
            x.push(obj.path[i][1] / scale);
            y.push(obj.path[i][2] / scale);
            pts.push({x: obj.path[i][1], y: obj.path[i][2]});
        }

        var data = {'r' : r, //r, x, y in stack coordinates
            'x' : x,
            'y' : y,
            'section' : stack.z,
            'id' : objectContainer.id,
            'assembly_id' : assemblyId,
            'left': o_left,
            'top': o_top,
            'scale' : scale,
            'view_left': view_left,
            'view_top' : view_top
        };

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": django_url + project.id + '/stack/' + stack.id + url,
            "data": data,
            "success": callback
        });
    };

    this.traceIdsInView = function(stack, callback)
    {
        var project = stack.getProject();
        var xMin = stack.screenPosition().left;
        var yMin = stack.screenPosition().top;
        var xMax = xMin + stack.viewWidth / stack.scale;
        var yMax = yMin + stack.viewHeight / stack.scale;
        var section = stack.z;

        var url = django_url + project.id + '/stack/' + stack.id + '/slice_ids_in_view';

        var data = {'x_min' : xMin,
            'y_min' : yMin,
            'x_max' : xMax,
            'y_max' : yMax,
            'section' : section};

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": callback
        })
    };

    this.retrieveTraces = function(ids, stack, callback)
    {
        var project = stack.getProject();
        var url = django_url + project.id + '/stack/' + stack.id + '/polygon_slices';

        var data = {'id' : ids};

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": callback
        });
    };

    this.createNewAssembly = function(stack, name, type, callback)
    {
        var project = stack.getProject();
        var url = django_url + project.id + '/stack/' + stack.id + '/create_new_assembly';

        var data = {'name' : name,
            'type': type};

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": callback
        });
    };

    this.retrieveAreas = function(stack, callback, regex)
    {
        var project = stack.getProject();
        var url = django_url + project.id + '/stack/' + stack.id + '/list_assemblies';
        var data;

        if (regex)
        {
            data = {'regex': regex};
        }
        else
        {
            data = {};
        }


        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": callback
        })
    };

    /**
     Sync display properties.
     */
    this.pushProperties = function(area)
    {

    };

    this.registerTool = function(tool)
    {
        areaTools.push(tool);
    };

    this.deregisterTool = function(tool)
    {
        // Remove the tool from the areaTools array.
        for (var idx = 0; idx < areaTools.length; ++i)
        {
            if( areaTools[idx] === tool)
            {
                areaTools.splice(idx, 1);
                return;
            }
        }
    };
};


/**
 Area class maintains geometric information for a given Assembly.
 */
function Area(name, assemblyId, canvasIn)
{
    this.color = 'rgb(255,0,0)';
    this.opacity = 1;
    this.name = name;
    this.assemblyId = assemblyId;

    var self = this;
    var canvas = canvasIn;
    var fabricObjects = [];
    var objectTable = {};

    this.transform = function(t)
    {
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].obj.transformMatrix(t);
        }
    };

    this.setOpacity = function(op)
    {
        self.opacity = op;
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].obj.opacity = op;
        }
        AreaServerModel.pushProperties(self);
    };

    this.getOpacity = function()
    {
        return self.opacity;
    };

    this.setColor = function(c)
    {
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            fabricObjects[idx].obj.setColor(c);
        }
        AreaServerModel.pushProperties(self);
    };

    this.getColor = function()
    {
        return self.color;
    };

    this.getObjects = function()
    {
        var objects = [];
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            objects.push(fabricObjects[idx].obj)
        }
        return objects;
    };

    this.setName = function(name)
    {
        self.name = name;
        AreaServerModel.pushProperties(self);
    };

    this.addObjectContainer = function(objectContainer)
    {
        var key = objectContainer.id;
        fabricObjects.push(objectContainer);
        objectTable[key] = objectContainer;
    };

    this.removeObject = function(key)
    {
        if (objectTable.hasOwnProperty(key))
        {
            var objectContainer = objectTable[key];
            var idx = fabricObjects.indexOf(objectContainer);
            canvas.remove(objectContainer.obj);
            fabricObjects.splice(idx, 1);
            delete objectTable[key];

            return objectContainer.obj;
        }
        else
        {
            return null;
        }
    };

    this.removeObjects = function(keys)
    {
        for (var idx = 0; idx < keys.length; ++idx)
        {
            self.removeObject(keys[idx]);
        }
    };

    this.hasObject = function(key)
    {
        return objectTable.hasOwnProperty(key);
    };

    this.updatePosition = function(screenPos, scale)
    {
        for (var i = 0; i < fabricObjects.length; ++i)
        {
            var c = fabricObjects[i];
            var obj = c.obj;
            var xs = c.stackLeft;
            var ys = c.stackTop;
            var xc = (xs - screenPos.left) * scale;
            var yc = (ys - screenPos.top) * scale;

            obj.scale(scale / c.originalScale);
            obj.setLeft(xc);
            obj.setTop(yc);
        }
    };

    this.keepTracesAtZ = function(z)
    {
        rmKeys = [];
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            if (fabricObjects[idx].z != z)
            {
                rmKeys.push(fabricObjects[idx].id);
            }
        }
        self.removeObjects(rmKeys);
    }
}


function FabricObjectContainer(obj, scale, screenPos, z, id)
{
    var self = this;

    var x_o = obj.getLeft();
    var y_o = obj.getTop();

    var x_s = screenPos.left;
    var y_s = screenPos.top;

    this.obj = obj;
    this.stackLeft = x_o / scale + x_s;
    this.stackTop = y_o / scale + y_s;
    this.originalScale = scale;
    this.id = id;
    this.z = z;
}

/**
 AreaTraceTool class handles area tracing operations
 */
function AreaTool()
{
    this.prototype = new Navigator();
    this.toolname = "Area Tracing Tool";
    this.width = 10;
    // Replaced when register() is called
    this.stack = null;
    this.lastPos = null;

    // mouse state
    // 0: nothing
    // 1: painting
    var mouseState = 0;
    var currentArea = null;
    var self = this;
    var actions = [];
    var areas = [];
    var nextId = 0;
    var assemblyTable = {};

    var proto_mouseCatcher = null;

    var isPainting = function()
    {
        return mouseState == 1;
    };

    var areaById = function(id)
    {
        if (assemblyTable.hasOwnProperty(id))
        {
            return assemblyTable[id];
        }
        else
        {
            return null;
        }
    };

    var setupProtoControls = function()
    {
        self.prototype.register( self.stack, "edit_button_area" );
        proto_mouseCatcher = self.prototype.mouseCatcher;
        proto_onmouseup = proto_mouseCatcher.onmouseup;
        proto_onmousedown = proto_mouseCatcher.onmousedown;
        proto_mouseCatcher.onmouseup = self.onmouseup;
        proto_mouseCatcher.onmousedown = self.onmousedown;
        proto_mouseCatcher.onmousemove = self.onmousemove;
    };

    var setupSubTools = function()
    {
        var box = createButtonsFromActions(
            actions,
            "toolbox_area",
            "area_");
        $( "#toolbox_area" ).replaceWith( box );
    };

    var createCanvasLayer = function()
    {
        self.canvasLayer = new AreaLayer( self.stack, self);
        var canvas = self.canvasLayer.canvas;

        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.width = self.width;
        canvas.isDrawingMode = true;

        canvas.on('path:created', function(e){
            if (currentArea != null)
            {
                self.registerFreshFabricObject(e.path);
            }
        });

        self.stack.addLayer("AreaLayer", self.canvasLayer);
        self.stack.resize();

        self.canvasLayer.view.onmousedown = self.onmousedown;
        self.canvasLayer.view.onmouseup = self.onmouseup;

        self.setCurrentArea(new Area("Dumb Area", 1, self.canvasLayer.canvas));
    };

    var currentZ = function()
    {
        return self.stack.z * self.stack.resolution.z + self.stack.translation.z;
    };

    var trimTraces = function()
    {
        for (var idx = 0; idx < areas.length; ++idx)
        {
            areas[idx].keepTracesAtZ(self.stack.z);
        }
    };

    var loadSVGFromURL = function(id, areaIn, section, replaceIds)
    {
        var sliceUrl = '/sopnet/' + self.stack.getProject().id + '/stack/' + self.stack.id +
            '/polygon_slice/' + id + '.svg';

        var svgCall = function(objects, options)
        {
            var obj = fabric.util.groupSVGElements(objects, options);
            var area = self.getArea(areaIn);

            obj.setColor(area.color);
            obj.setOpacity(area.opacity);

            self.registerDeserializedFabricObject(obj, area, id, section);
            self.canvasLayer.canvas.add(obj);

            area.updatePosition(self.stack.screenPosition(), self.stack.scale);

            if (replaceIds != undefined && replaceIds != null)
            {
                for (var idx = 0; idx < replaceIds.length; ++idx)
                {
                    var rmObj = area.removeObject(replaceIds[idx]);
                    //self.canvasLayer.canvas.remove(rmObj);
                }
            }
        };

        fabric.loadSVGFromURL(sliceUrl, svgCall);
    };

    var pushTraceCallback = function(data)
    {
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
            growlAlert('Error', 'Problem retrieving trace. See console');
        }
        else
        {
            var svgCall = function(objects, options)
            {
                var obj = fabric.util.groupSVGElements(objects, options);
                var area = self.getArea(data.assembly_id);

                obj.setColor(data.view_props.color);
                obj.setOpacity(data.view_props.color);

                self.registerDeserializedFabricObject(obj, area, data.id, data.section);
                self.canvasLayer.canvas.add(obj);

                area.updatePosition(self.stack.screenPosition(), self.stack.scale);

                if (data.hasOwnProperty('replace_ids') && data.replace_ids != null)
                {
                    for (var idx = 0; idx < data.replace_ids.length; ++idx)
                    {
                        var rmObj = area.removeObject(data.replace_ids[idx]);
                        self.canvasLayer.canvas.remove(rmObj);
                    }
                }
            };

            loadSVGFromURL(data.id, svgCall);
        }

    };

    var checkAreaAndTrace = function(areaIn, id)
    {
        var area = self.getArea(areaIn);
        if (area == null)
        {
            return false;
        }
        else
        {
            return area.hasObject(id);
        }
    };

    var retrieveTracesCallback = function(data)
    {
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
            growlAlert('Error', 'Problem fetching traces. See console');
        }
        else
        {
            for (var idx = 0; idx < data.areas.length; ++idx)
            {
                pushTraceCallback(data.areas[idx]);
            }

            trimTraces();
        }
    };

    var sliceIdsCallback = function(data)
    {
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
            growlAlert('Error', 'Problem retrieving trace ids. See console');
        }
        else
        {
            var needIds = [];
            for (var idx = 0; idx < data.ids.length; ++idx)
            {
                if (!checkAreaAndTrace(data.assembly_ids[idx], data.ids[idx]))
                {
                    loadSVGFromURL(data.ids[idx], data.assembly_ids[idx], self.stack.z);
                }
            }
        }

    };

    this.fetchAreas = function()
    {
        AreaServerModel.traceIdsInView(self.stack, sliceIdsCallback);
    };

    this.addAction = function ( action ) {
        actions.push( action );
    };

    this.getActions = function () {
        return actions;
    };

    this.setWidget = function(widgetIn)
    {
        widget = widgetIn;
    };

    this.addAction( new Action({
        helpText: "Area editting tool",
        buttonName: "editor",
        buttonID: "area_edit_button",
        run: function(e) {
            areaWindow = WindowMaker.show('area-editting-tool');
            if (areaWindow.hasOwnProperty('areaWidget'))
            {
                areaWindow.areaWidget.setTool(self);
            }
            return true;
        }
    }));

    this.onmousemove = function(e)
    {
        if (e.button == 0 && isPainting())
        {
            self.canvasLayer.canvas._onMouseMoveInDrawingMode(e);
            return true;
        }
    };

    this.onmousedown = function(e)
    {
        // Do some drawing! But only if we have an active area to trace and we're using the left
        // mouse button.
        if (currentArea != null && e.button == 0)
        {
            // Now we're painting.
            mouseState = 1;
            self.canvasLayer.canvas._onMouseDownInDrawingMode(e);
            return true;
        }
        // Otherwise, pass the event through to the prototype navigator.
        else if(e.button == 1)
        {
            proto_onmousedown(e);
            return true;
        }
    };

    this.onmouseup = function(e)
    {
        if (e.button == 1 && isPainting())
        {
            mouseState = 0;
            proto_onmouseup(e);
            return true;
        }
        else if (e.button == 0)
        {
            self.canvasLayer.canvas._onMouseUpInDrawingMode(e);
            return true;
        }
    };

    this.getArea = function(areaIdentifier)
    {
        var areaType = typeof areaIdentifier;

        if (areaType == 'undefined')
        {
            return currentArea;
        }
        else if(areaType == 'object')
        {
            return areaIdentifier;
        }
        else if (areaType == 'number')
        {
            return areaById(areaIdentifier);
        }
        else
        {
            console.log('Unexpected area type');
            return null;
        }
    };

    this.registerDeserializedFabricObject = function(obj, areaIn, id, zIn, scaleIn,
                                                     screenRelativePositionIn)
    {
        var area = self.getArea(areaIn);
        var scale = 1.0;
        var screenRelativePosition = null;
        var z = zIn;

        obj.setOriginX('center');
        obj.setOriginY('center');

        if (typeof scaleIn != 'undefined')
        {
            scale = scaleIn;
        }

        if (typeof screenRelativePositionIn == 'undefined')
        {
            screenRelativePosition = {left: 0, top: 0};
        }
        else
        {
            screenRelativePosition = screenRelativePositionIn;
        }

        if (typeof zIn == 'undefined')
        {
            z = self.stack.z;
        }

        var objectContainer = new FabricObjectContainer(obj, scale, screenRelativePosition, z, id);
        area.addObjectContainer(objectContainer);

        area.updatePosition(self.stack.screenPosition(), self.stack.scale);

        self.canvasLayer.canvas.renderAll();

        return objectContainer;
    };

    /**
     * Register a fabric.js Object to an Area
     *
     * @param obj the fabric.js object to register
     * @param areaIn the area identifier, one of:
     *        undefined - use the currentArea of this tool
     *        object - use this Area object
     *        number - use the Area with this assembly id
     */
    this.registerFreshFabricObject = function(obj, areaIn)
    {
        var area = self.getArea(areaIn);
        var objectContainer = new FabricObjectContainer(obj, self.stack.scale,
            self.stack.screenPosition(), self.stack.z, nextId++);

        area.addObjectContainer(objectContainer);

        AreaServerModel.pushTrace(self.stack, self.width, currentArea.assemblyId,
            objectContainer, pushTraceCallback);
    };


    this.register = function(parentStack)
    {
        g_AreaTool = self;
        g_Nav = self.prototype;

        if (self.stack == null)
        {
            self.stack = parentStack;

            $("#toolbox_area").show();

            $("#edit_button_area").switchClass("button", "button_active", 0);

            self.prototype.register(parentStack, "edit_button_area");

            setupSubTools();
            createCanvasLayer();
            setupProtoControls();
            self.fetchAreas();

            AreaServerModel.registerTool(self);
        }
    };

    this.unregister = function()
    {
        //self.prototype.destroy( "edit_button_area" );
    };

    this.destroy = function()
    {
        $("#edit_button_area").switchClass("button_active", "button", 0);
        $("#toolbox_area").hide();
    };

    this.resize = function(height, width)
    {
        self.canvasLayer.resize(height, width);
    };

    this.cacheScreenParameters = function()
    {
        self.lastPos = self.stack.screenPosition();
        self.lastScale = self.stack.scale;
        self.lastZ = currentZ();
    };

    this.redraw = function() {

        if (self.lastPos)
        {
            if (self.lastZ != self.stack.z)
            {
                self.fetchAreas();
                trimTraces();
            }

            self.cacheScreenParameters();

            for (i = 0; i < areas.length; ++i)
            {
                areas[i].updatePosition(self.stack.screenPosition(), self.stack.scale);
            }
        }
        else
        {
            self.cacheScreenParameters();
        }

        self.canvasLayer.canvas.renderAll();
    };

    this.setArea = function(area)
    {
        currentArea = area;
    };

    this.getArea = function()
    {
        return currentArea;
    };

    this.hasAreaWithId = function(id)
    {
        return assemblyTable.hasOwnProperty(id);
    };

    this.setCurrentArea = function(area)
    {
        if (!self.hasAreaWithId(area.assemblyId))
        {
            self.addArea(area);
        }

        currentArea = area;
    };

    this.addArea = function(area)
    {
        assemblyTable[area.assemblyId] = area;
        areas.push(area);
    };

    /**
     * This function should return true if there was any action
     * linked to the key code, or false otherwise.
     */
    this.handleKeyPress = function( e )
    {
        var keyAction = keyCodeToAction[e.keyCode];
        if (keyAction) {
            return keyAction.run(e);
        } else {
            return false;
        }
    };

    var keyCodeToAction = getKeyCodeToActionMap(actions);

}

var AreaTraceWidget = function() {};

AreaTraceWidget.prototype = {};

/**
 * Initializes the area tool widget in the given container.
 *
 * Most of the following code was cribbed from settings.js
 */
AreaTraceWidget.prototype.init = function(space) {
    var tool = null;
    var assemblySelectElement = null;
    var self = this;

    var selectAssembly = function()
    {
        console.log(this);
    };

    var updateAssemblySearchBox = function()
    {

    };

    var updateAssemblySettings = function(regex)
    {
        AreaServerModel.retrieveAreas(tool.stack,
            self.updateAssemblySelect,
            regex);
    };

    this.setTool = function(inTool)
    {
        tool = inTool;
        updateAssemblySettings();
        /*AreaServerModel.retrieveAreas(tool.stack,
        function(data)
        {
            self.updateAssemblySelect(data);
        })*/
    };

    this.updateAssemblySelect = function(data)
    {
        if (assemblySelectElement != null)
        {
            var assemblies = data.assemblies;
            var currentArea = tool.getArea();
            var selectText = '';
            var idx;

            for (idx = 0; idx < assemblySelectElement[0].length; ++idx)
            {
                assemblySelectElement[0].remove(0)
            }

            if (assemblies.length > 0) {
                for (idx = 0; idx < assemblies.length; ++idx) {
                    var assy = assemblies[idx];

                    if (assy.name == currentArea.name)
                    {
                        selectText = 'selected';
                    }
                    else
                    {
                        selectText = '';
                    }

                    var optionString = '<option ' + selectText +
                        ' value="' + assy.id + '">' +
                        assy.name + ' (' + assy.type + ')</option>';
                    assemblySelectElement.append(optionString).css('color', assy.color);
                }
            }
            else
            {
                assemblySelectElement.append('<option/>');
            }
        }
    };

    /**
     * Helper function to create a collapsible settings container.
     */
    var addSettingsContainer = function (parent, name, closed) {
        var content = $('<div/>').addClass('content');
        if (closed) {
            content.css('display', 'none');
        }
        var sc = $('<div/>')
            .addClass('settings-container')
            .append($('<p/>')
                .addClass('title')
                .append($('<span/>')
                    .addClass(closed ? 'extend-box-closed' : 'extend-box-open'))
                .append(name))
            .append(content);

        $(parent).append(sc);

        return content;
    };

    /**
     * Helper function to add a labeled control.
     */
    var createLabeledControl = function (name, control) {
        return $('<div/>').addClass('setting')
            .append($('<label/>')
                .append($('<span/>').addClass('description').append(name))
                .append(control));
    };

    /**
     * Helper function to create a checkbox with label.
     */
    var createCheckboxSetting = function (name, handler) {
        var cb = $('<input/>').attr('type', 'checkbox');
        if (handler) {
            cb.change(handler);
        }
        var label = $('<div/>')
            .addClass('setting')
            .append($('<label/>').append(cb).append(name));

        return label;
    };

    var createAssemblySelector = function(handler)
    {
        var selectElement = $('<select id="selectAssembly" name="selectAssembly" size="12">' +
            '</select>');
        var regexInput = $('<input name="assembly_regex" id="assemblyRegexInput"/>');

        var searchButton = $('<button/>').text('Search').click(
            function()
            {
                updateAssemblySettings(regexInput.val());
            }
        );

        var createButton = $('<button/>').text('Create New').click(
            function()
            {
                var newAssemblyInput = $('<input name="new_assembly_input" />');
                var newAssemblyType = $('<select name="new_assembly_select"/>').append(
                    '<option selected value="neuron">Neuron</option>'
                ).append(
                    '<option value="synapse">Synapse</option>'
                ).append(
                    '<option value="mitochondrion">Mitochondria</option>'
                ).append(
                    '<option value="glia">Glia</option>'
                );

                var okButton = $('<button/>').text('OK').click(
                    function()
                    {
                        $.unblockUI();
                        console.log(newAssemblyInput.val());
                        console.log(newAssemblyType.value);
                        AreaServerModel.createNewAssembly(tool.stack, newAssemblyInput.val(),
                            newAssemblyType.val(), self.updateAssemblySelect);
                    }
                );

                var cancelButton = $('<button/>').text('Cancel').click(
                    function()
                    {
                        $.unblockUI();
                    }
                );

                var newAssemblyDiv = $('<div/>').append('Name:').append(newAssemblyInput);
                newAssemblyDiv.append('Type:').append(newAssemblyType).append('<br>');
                newAssemblyDiv.append(okButton).append(cancelButton);
                newAssemblyDiv.css({width: 500});

                $.blockUI({message: newAssemblyDiv});
            }
        );

        selectElement.change(selectAssembly);

        var selector = $('<div/>').append(selectElement).append(regexInput).append(searchButton).append(createButton);

        return selector;
    };

    /**
     * Helper function to create a text input field with label.
     */
    var createInputSetting = function (name, val, handler) {
        var input = $('<input/>').attr('type', 'text').val(val);
        return createLabeledControl(name, input);
    };

    var createAssemblyManager = function()
    {
        var assemblySelectDiv = createAssemblySelector();


        assemblySelectDiv.css({width: '200px', float: 'left'});

        var managerDiv = $('<div/>').append(assemblySelectDiv);

        return managerDiv;
    };

    /*
     * Adds an Assembly selector
     */
    var addAssemblyManager = function (container) {
        var ds = addSettingsContainer(container, "Assemblies");

        var assemblyManagerDiv = createAssemblyManager();

        //var assemblySelectDiv = createAssemblySelector(selectAssembly);
        $(ds).append(assemblyManagerDiv);
        assemblySelectElement = $('#selectAssembly');
    };



    addAssemblyManager(space);

    // Add collapsing support to all settings containers
    $("p.title", space).click(function () {
        var section = this;
        $(section).next(".content").animate(
            { height: "toggle",
                opacity: "toggle" },
            { complete: function () {
                // change open/close indicator box
                var open_elements = $(".extend-box-open", section);
                if (open_elements.length > 0) {
                    open_elements.attr('class', 'extend-box-closed');
                } else {
                    $(".extend-box-closed", section).attr('class', 'extend-box-open');
                }
            }});
    });
};