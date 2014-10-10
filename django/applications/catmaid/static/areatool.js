

/*
Nomenclature:

Area: a representation of a generic object, which may be neuron, mito, glia, etc., consisting
      of one or more Traces

Trace: a single geometric representation. Currently, Trace' are polygonal, but the future may bring
       traces represented as bitmaps. Essentially, a Trace is a 2D geometry associated with a
       section and makes up a portion of an Area.

Assembly: The database representation of an Area, essentially analogous.

Slice: This is the Sopnet name for what we call a Trace, and therefore also the name of the
       Trace representation in the database.

 */



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

    this.tracesInView = function(stack, callback)
    {
        var project = stack.getProject();
        var xMin = stack.screenPosition().left;
        var yMin = stack.screenPosition().top;
        var xMax = xMin + stack.viewWidth / stack.scale;
        var yMax = yMin + stack.viewHeight / stack.scale;
        var section = stack.z;

        var url = django_url + project.id + '/stack/' + stack.id + '/slices_in_view';

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

    this.retrieveAreas = function(stack, callback, dataIn)
    {
        var project = stack.getProject();
        var url = django_url + project.id + '/stack/' + stack.id + '/list_assemblies';
        var data;

        if (dataIn)
        {
            data = dataIn;
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
function Area(name, assemblyId, canvasIn, viewProps)
{
    var self = this;
    var canvas = canvasIn;
    var fabricObjects = [];
    var objectTable = {};

    if (viewProps)
    {
        this.color = viewProps.color;
        this.opacity = viewProps.opacity;
    }
    else
    {
        this.color = '#ff8800';
        this.opacity = 0.5;
    }

    this.name = name;
    this.assemblyId = assemblyId;

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
        if (!objectTable.hasOwnProperty(key))
        {
            fabricObjects.push(objectContainer);
            objectTable[key] = objectContainer;
        }
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
    var toolMode = '';

    var toolModeNames = {
        paint: 'Paint Brush',
        erase: 'Eraser',
        fill: 'Close Holes',
        select: 'Select',
        stamp: 'Stamp'
    };

    var enterModeFunctions = {};
    var leaveModeFunctions = {};

    // ui change callback
    var uiChange = function(){};

    var proto_mouseCatcher = null;

    var isPainting = function()
    {
        return mouseState == 1;
    };

    var enterPaintingMode = function()
    {
        self.canvasLayer.canvas.isDrawingMode = true;
    };

    var leavePaintingMode = function()
    {
        self.canvasLayer.canvas.isDrawingMode = false;
    };

    var setSelectMode = function()
    {

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

    var readSVGAreaFromURL = function(id, areaIn, section, replaceIds)
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
                    self.canvasLayer.canvas.remove(rmObj);
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

            readSVGAreaFromURL(data.id, data.assembly_id, data.section, data.replace_ids);
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

    var slicesCallback = function(data)
    {
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
            growlAlert('Error', 'Problem retrieving trace ids. See console');
        }
        else
        {
            var areaData = data.assemblies;
            var traceData = data.slices;
            var idx;
            var section = data.section;

            for (idx = 0; idx < areaData.length; ++idx)
            {
                self.getOrCreateArea(areaData[idx]);
            }

            for (idx = 0; idx < traceData.ids.length; ++idx)
            {



                if (!checkAreaAndTrace(traceData.assembly_ids[idx], traceData.ids[idx]))
                {
                    readSVGAreaFromURL(traceData.ids[idx], traceData.assembly_ids[idx], section);
                }
            }
        }

    };

    var objectMouseDown = function(e)
    {
        console.log(e);
    };

    this.getOrCreateArea = function(areaData)
    {
        if (self.hasAreaWithId(areaData.id))
        {
            return self.getArea(areaData.id);
        }
        else
        {
            var area = new Area(areaData.name, areaData.id, self.canvasLayer.canvas, areaData);
            self.addArea(area);
            return area;
        }
    };

    this.fetchAreas = function()
    {
        AreaServerModel.tracesInView(self.stack, slicesCallback);
    };

    this.addAction = function ( action ) {
        actions.push( action );
    };

    this.getActions = function () {
        return actions;
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

    this.getAreas = function()
    {
        return areas;
    };

    this.onmousemove = function(e)
    {
        if (e.button == 0 && isPainting())
        {
            self.canvasLayer.canvas._onMouseMoveInDrawingMode(e);
            return true;
        }
        else
        {
            return false;
        }
    };

    this.onmousedown = function(e)
    {
        // Do some drawing! But only if we have an active area to trace and we're using the left
        // mouse button.
        if (e.button == 0)
        {
            if (toolMode == 'paint' && currentArea != null)
            {
                // Now we're painting.
                mouseState = 1;
                self.canvasLayer.canvas._onMouseDownInDrawingMode(e);
                return true;
            }
            else
            {
                //self.canvasLayer.canvas._onMouseDown(e);
                return true;
            }
        }
        // Otherwise, pass the event through to the prototype navigator.
        else
        {
            proto_onmousedown(e);
            return true;
        }
    };

    this.onmouseup = function(e)
    {
        if (e.button == 0 && isPainting())
        {
            self.canvasLayer.canvas._onMouseUpInDrawingMode(e);
            return true;
        }
        else
        {
            mouseState = 0;
            proto_onmouseup(e);
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
        else if (areaType == 'number' || areaType == 'string')
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
        obj.on('mouse:down', objectMouseDown);

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

        obj.on('mouse:down', objectMouseDown);
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

    this.setMode = function(mode)
    {
        if (toolModeNames.hasOwnProperty(mode))
        {
            if (leaveModeFunctions.hasOwnProperty(toolMode))
            {
                leaveModeFunctions[toolMode]();
            }

            toolMode = mode;

            if (enterModeFunctions.hasOwnProperty(mode))
            {
                enterModeFunctions[mode]();
            }

            uiChange();
        }
    };

    this.getMode = function()
    {
        return toolMode;
    };

    this.modeToString = function(inMode)
    {
        var mode;
        if (typeof inMode == 'undefined')
        {
            mode = toolMode;
        }
        else
        {
            mode = inMode;
        }

        return toolModeNames[mode];
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

    /**
     * Set a callback function for changes made to tool parameters by key+mouse events, for
     * instance, when the user changes brush size by holding shift and rolling the mouse wheel.
     *
     * In particular, this function will not be called upon creation of a new trace.
     *
     * @param fun a callback function, to be called with no arguments.
     */
    this.change = function(fun)
    {
        uiChange = fun;
    };

    var keyCodeToAction = getKeyCodeToActionMap(actions);

    enterModeFunctions['paint'] = enterPaintingMode;
    leaveModeFunctions['paint'] = leavePaintingMode;

    self.setMode('select');

}

var AreaTraceWidget = function() {};

AreaTraceWidget.prototype = {};

/**
 * Initializes the area tool widget in the given container.
 *
 * A lot of the following code was cribbed from settings.js
 */
AreaTraceWidget.prototype.init = function(space) {
    var self = this;
    var tool = null;
    var assemblySelectElement = null;

    var toolModeLabel = $('<div id="area_toolmode_label"/>');

    $(space).append(toolModeLabel);

    /**
     * Helper function to create a checkbox with label.
     */
    var createCheckboxHelper = function (name, handler) {
        var cb = $('<input/>').attr('type', 'checkbox');
        if (handler) {
            cb.change(handler);
        }
        var label = $('<div/>')
            .append($('<label/>').append(cb).append(name));

        return label;
    };

    this.redraw = function()
    {
        toolModeLabel.html('');
        var nameStr;

        if (tool != null)
        {
            var area = tool.getArea();
            nameStr = area == null ? '' : ': ' +  area.name;
        }

        toolModeLabel.append(tool.modeToString() + nameStr);

        self.updateToolSelector();
    };

    /*===== Tool Selector =====*/

    /*
    Available tool modes:
    'paint': additively paint Areas
    'erase': subtractively paint Areas
    'fill': fill holes in the given area
    'select': select an area by clicking on it
    'stamp': click to add a predefined polygon to the Area
     */

    var toolActions = [];
    var toolOptionDivs = {};
    var toolboxOptionsDiv;
    var maxBrushSize = 128;
    var toolModeNames = {
        paint: 'Paint Brush',
        erase: 'Eraser',
        fill: 'Close Holes',
        select: 'Select',
        stamp: 'Stamp'
    };

    this.addAction = function(action)
    {
        toolActions.push(action);
    };

    this.updateToolSelector = function()
    {
        toolboxOptionsDiv.html('');

        toolboxOptionsDiv.append(toolOptionDivs[tool.getMode()]);
    };

    var setAutoFill = function()
    {
        console.log(this.checked);
    };

    var setBrushSize = function()
    {
        console.log(this.val);
    };

    var setFillMode = function()
    {
        console.log(this.value);
    };

    var createPaintOptions = function()
    {
        // options div.
        var od = $('<div id="area_paint_options"/>');
        var sliderDiv = $('<div id="area_paint_size_slider" />');

        var brushSizeSlider  = new Slider(SLIDER_HORIZONTAL, true, 1, maxBrushSize, maxBrushSize,
            16, setBrushSize);
        var autoFillCheckbox = createCheckboxHelper('Automatically Fill Holes', setAutoFill);

        sliderDiv.append('Brush Size').append('<br>');
        sliderDiv.append(brushSizeSlider.getView());
        sliderDiv.append(brushSizeSlider.getInputView());

        od.append(sliderDiv).append('<br>').append(autoFillCheckbox);

        return od;
    };

    var createEraseOptions = function()
    {
        // options div.
        var od = $('<div id="area_erase_options"/>');
        var sliderDiv = $('<div id="area_erase_size_slider" />');

        var brushSizeSlider  = new Slider(SLIDER_HORIZONTAL, true, 1, maxBrushSize, maxBrushSize,
            16, setBrushSize);

        sliderDiv.append('Brush Size').append('<br>');
        sliderDiv.append(brushSizeSlider.getView());
        sliderDiv.append(brushSizeSlider.getInputView());

        od.append(sliderDiv);

        return od;
    };

    var createFillOptions = function()
    {
        // options div.
        var od = $('<div id="area_fill_options"/>');
        var one = $('<input type="radio" name="area_fill_radio" value="one">Fill One Hole</input>');
        var all = $('<input type="radio" name="area_fill_radio" value="all">Fill All Holes</input>');

        one.change(setFillMode);
        all.change(setFillMode);

        od.append(one).append('<br>').append(all);

        return od;
    };

    var createStampOptions = function()
    {
        return $('<div/>');
    };

    var createToolBoxDiv = function()
    {
        var toolbox = createButtonsFromActions(toolActions, 'area_tool_box', 'area_tool_');
        toolOptionDivs['paint'] = createPaintOptions();
        toolOptionDivs['erase'] = createEraseOptions();
        toolOptionDivs['fill'] = createFillOptions();
        toolOptionDivs['select'] = $('<div/>');
        toolOptionDivs['stamp'] = createStampOptions();

        toolboxOptionsDiv = $('<div id="area_toolbox_options"/>');

        return $('<div id="area_toolbox" />').append(toolbox).append('<br>').
            append(toolboxOptionsDiv);
    };

    var addAssemblyToolBox = function(container)
    {
        //$(container).append(createToolBoxDiv());
        var tb = addSettingsContainer(container, "Tools");
        var toolBoxDiv = createToolBoxDiv();
        $(tb).append(toolBoxDiv);
    };

    /*===== Assembly Property Editor =====*/

    var colorWheel;
    var opacitySlider;

    /**
     * Update the color wheel and opacity slider values to the tool.currentArea
     */
    var updatePropertyEditor = function()
    {

    };

    /**
     * Set the opacity of tool.currentArea according to the opacity slider.
     */
    var setToolOpacity = function()
    {

    };

    /**
     * Set the color of tool.currentArea according to the colorwheel.
     */
    var setToolColor = function()
    {

    };

    /**
     * Send the view property values for the current area to the server.
     */
    var syncServerViewProps = function()
    {

    };

    var createOpacitySlider = function()
    {
        var sliderDiv = $('<div id="area_opacity_slider" />');
        opacitySlider  = new Slider(SLIDER_HORIZONTAL, true, 1, 100, 100,
                0, setToolOpacity);

        sliderDiv.append('Opacity').append('<br>');
        sliderDiv.append(opacitySlider.getView());
        sliderDiv.append(opacitySlider.getInputView());

        return sliderDiv;
    };

    var createColorWheel = function()
    {
        var cwDiv = $('<div id="assembly_color_wheel"/>');
        colorWheel = Raphael.colorwheel(cwDiv, 150);
        return cwDiv;
    };

    var createPropertyEditor = function()
    {
        var opacitySliderDiv = createOpacitySlider();
        var colorWheelDiv = createColorWheel();

        var propertyEditorDiv = $('<div/>').append(opacitySliderDiv).append('<br>');
        propertyEditorDiv.append(colorWheelDiv);

        return propertyEditorDiv;
    };

    var addAssemblyPropertyEditor = function(container)
    {
        var ds = addSettingsContainer(container, "Properties");

        var propertiesDiv = createPropertyEditor();

        $(ds).append(propertiesDiv);
    };

    /*===== Assembly Manager =====*/

    this.searchOptions = {'visible_only': false,
        'in_view_only': false,
        'regex': ''};

    var updateSearchSettings = function()
    {
        AreaServerModel.retrieveAreas(tool.stack,
            self.updateAssemblySelect,
            self.searchOptions);
    };

    var selectAssembly = function()
    {
        // In this scope, this === $('#selectAssembly')[0] should return True.
        area = tool.getOrCreateArea({
            name: this.name,
            id: this.value,
            color: this.getAttribute('area_color'),
            opacity: this.getAttribute('area_opacity')});
        tool.setCurrentArea(area);
        self.redraw();
    };

    /**
     * Update the assembly select element, $('#selectAssembly'). For use as an ajax callback.
     * @param data an ajax callback Object, with the following properties:
     *      assemblies - an array of Objects with properties:
     *          name - area name
     *          color - area color
     *          opacity - area opacity
     *          id - area id
     */
    this.updateAssemblySelect = function(data)
    {
        if (assemblySelectElement != null)
        {
            var assemblies = data.assemblies;
            var currentArea = tool.getArea();
            var selectText = '';
            var idx;
            var n = assemblySelectElement[0].length;

            for (idx = 0; idx < n; ++idx)
            {
                assemblySelectElement[0].remove(0)
            }

            if (assemblies.length > 0) {
                for (idx = 0; idx < assemblies.length; ++idx) {
                    var assy = assemblies[idx];

                    tool.getOrCreateArea(assy);

                    if (currentArea != null && assy.name == currentArea.name)
                    {
                        selectText = 'selected';
                    }
                    else
                    {
                        selectText = '';
                    }

                    var optionString = '<option ' + selectText +
                        ' name="' + assy.name + '" ' +
                        ' area_color="' + assy.color + '" ' +
                        ' area_opacity="' + assy.opacity + '" ' +
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

    var createAssemblyButtonClick = function()
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

        var newAssemblyDiv = $('<div/>').append('Name:').append(newAssemblyInput);

        var okButton = $('<button/>').text('OK').click(
            function()
            {
                $.unblockUI();
                AreaServerModel.createNewAssembly(tool.stack, newAssemblyInput.val(),
                    newAssemblyType.val(), self.updateAssemblySelect);
            }
        );

        var cancelButton = $('<button/>').text('Cancel').click(
            function()
            {
                $.unblockUI();
                newAssemblyDiv.remove();
            }
        );


        newAssemblyDiv.append('Type:').append(newAssemblyType).append('<br>');
        newAssemblyDiv.append(okButton).append(cancelButton);
        newAssemblyDiv.css({width: '350px'});

        $.blockUI({message: newAssemblyDiv});
    };


    /**
     * Generate the Assembly Selector. This is the part of the widget that allows for searching and
     * selecting different Areas/Assemblies.
     */
    var createAssemblySelector = function()
    {
        var selectElement = $('<select id="selectAssembly" name="selectAssembly" size="12">' +
            '</select>');
        var regexInput = $('<input name="assembly_regex" id="assemblyRegexInput"/>');

        var searchButton = $('<button/>').text('Search').click(
            function()
            {
                self.searchOptions['regex'] = regexInput.val();
                updateSearchSettings();
            }
        );

        var clearSearchButton = $('<button/>').text('Clear').click(
          function()
          {
              regexInput.val('');
              self.searchOptions['regex'] = '';
              updateSearchSettings();
          }
        );

        var createButton = $('<button/>').text('Create New').click(createAssemblyButtonClick);

        selectElement.change(selectAssembly);

        // <select> element, listing the available areas
        var selector = $('<div/>').append(selectElement).append('<br>');

        // Search input box, search and clear buttons.
        selector.append(regexInput).append(searchButton).append(clearSearchButton).append('<br>');

        // Create new button
        selector.append(createButton);

        return selector;
    };

    var createAssemblySearchOptions = function()
    {
        // In the following handler functions' scopes, this points to the
        // checkbox element.
        var visibleOnly = createCheckboxHelper('Visible Areas Only',
            function()
            {
                self.searchOptions['visible_only'] = this.value == "on";
                updateSearchSettings();
            }
        );

        var inViewOnly = createCheckboxHelper('Areas in View Only',
            function()
            {
                self.searchOptions['in_view_only'] = this.value == "on";
                updateSearchSettings();
            }
        );

        var options = $('<div/>').append(visibleOnly).append('<br>').append(inViewOnly);
        return options;
    };

    var createAssemblyManager = function()
    {
        var assemblySelectDiv = createAssemblySelector();
        var assemblySearchOptionDiv = createAssemblySearchOptions();

        assemblySelectDiv.css({width: '350px', float: 'left'});
        assemblySearchOptionDiv.css({width: '350px', float: 'left'});

        var managerDiv = $('<div/>').append(assemblySelectDiv).append(assemblySearchOptionDiv);

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


    this.setTool = function(inTool)
    {
        tool = inTool;
        tool.change(self.redraw);
        updateSearchSettings();
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
     * Helper function to create a text input field with label.
     */
    var createInputSetting = function (name, val, handler) {
        var input = $('<input/>').attr('type', 'text').val(val);
        return createLabeledControl(name, input);
    };

    // Add tools for the toolbox
    this.addAction(new Action({
        helpText: "Paint Brush",
        buttonName: "paint_brush",
        buttonID: "area_paint_brush",
        run: function (e) {
            tool.setMode('paint');
            return true;
        }
    }));

    this.addAction(new Action({
        helpText: "Eraser",
        buttonName: "eraser",
        buttonID: "area_eraser",
        run: function (e) {
            tool.setMode('erase');
            return true;
        }
    }));

    this.addAction(new Action({
        helpText: "Close Holes",
        buttonName: "fill_holes",
        buttonID: "area_fill_holes",
        run: function (e) {
            tool.setMode('fill');
            return true;
        }
    }));

    this.addAction(new Action({
        helpText: "Select Areas",
        buttonName: "selector",
        buttonID: "area_selector",
        run: function (e) {
            tool.setMode('select');
            return true;
        }
    }));

    this.addAction(new Action({
        helpText: "Stamp!",
        buttonName: "stamp",
        buttonID: "area_stamp",
        run: function (e) {
            tool.setMode('stamp');
            return true;
        }
    }));



    addAssemblyToolBox(space);
    addAssemblyPropertyEditor(space);
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