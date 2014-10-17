

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
    var self = this;

    this.sopnet_url = django_url + 'sopnet/';

    this.defaultColor = '#0000ff';
    this.defaultOpacity = 0.5;

    /**
     * Close a hole in a trace at a given location
     * @param stack the current stack
     * @param assemblyId the id of the assembly to which this trace will be added
     * @param location the location of the hole to be closed, in screen coordinates, like
     *  {x: 100, y: 205.5}
     * @param all true to close all holes, false to close only the hole that was clicked on.
     * @param callback a function to be called with the data returned by ajax.
     */
    this.closeHole = function(stack, assemblyId, location, all, callback)
    {
        var view_top = stack.screenPosition().top;
        var view_left = stack.screenPosition().left;
        var scale = stack.scale;
        var x = location.x / scale + view_left;
        var y = location.y / scale + view_top;

        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/close_hole';

        var data = {'x': x,
            'y': y,
            'section': stack.z,
            'assembly_id': assemblyId,
            'all': all
        };

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": callback
        });
    };


    /**
     *  Push a new trace (ie, fabricjs path object) to the backend.
     * @param stack the current stack
     * @param brushWidth the width, or diameter, of the brush
     * @param assemblyId the id of the assembly to which this trace will be added
     * @param objectContainer the container holding the fabric path object
     * @param mode - 'paint' or 'erase'
     * @param opts a set of options, with the following optional fields:
     *      close - set true to ignore holes
     *      closeAll - set true to remove holes from the resulting merge, as well.
     *      opts is ignored for erase mode.
     * @param callback a function to be called with the data returned by ajax.
     */
    this.pushTrace = function(stack, brushWidth, assemblyId, objectContainer, opts, callback)
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

        if (opts)
        {
            data.close = opts.close;
            data.closeAll = opts.closeAll;
        }
        else
        {
            data.close = false;
            data.closeAll = false;
        }

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": self.sopnet_url + project.id + '/stack/' + stack.id + url,
            "data": data,
            "success": callback
        });
    };

    this.erase = function(stack, brushWidth, assemblyId, objectContainer, callback)
    {
        var x = [];
        var y = [];
        var pts = [];
        var obj = objectContainer.obj;
        var project = stack.getProject();
        var view_top = stack.screenPosition().top;
        var view_left = stack.screenPosition().left;
        var scale = stack.scale;
        var url = '/erase';
        var bound_rect = obj.getBoundingRect();
        var o_left = (bound_rect.left + (brushWidth / 2.0)) / scale + view_left;
        var o_top = (bound_rect.top + (brushWidth / 2.0)) / scale + view_top;
        var r = brushWidth / (2.0 * scale);

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
            "url": self.sopnet_url + project.id + '/stack/' + stack.id + url,
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

        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/slices_in_view';

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
        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/polygon_slices';

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
        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/create_new_assembly';

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
        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/list_assemblies';
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
    this.pushProperties = function(stack, area)
    {
        var project = stack.getProject();
        var url = self.sopnet_url + project.id + '/stack/' + stack.id + '/set_view_properties';
        var data =
        {
            assembly_id: area.assemblyId,
            color: area.color,
            opacity: area.opacity,
            name: area.name
        };

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": url,
            "data": data,
            "success": function(data)
            {
                if (!data.hasOwnProperty('ok') || !data.ok)
                {
                    growlAlert('Error', 'Problem setting properties. See console.');
                    if (data.hasOwnProperty('djerror'))
                    {
                        console.log(data.djerror);
                    }
                    else
                    {
                        console.log(data);
                    }
                }
            }
        })
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
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            fabricObjects[idx].obj.transformMatrix(t);
        }
    };

    this.setOpacity = function(op)
    {
        self.opacity = op;
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            fabricObjects[idx].obj.opacity = op;
        }
        canvas.renderAll();
        //AreaServerModel.pushProperties(self);
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

        self.color = c;

        canvas.renderAll();
        //AreaServerModel.pushProperties(self);
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

    this.containsPoint = function(pt)
    {
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            if (fabricObjects[idx].obj.containsPoint(pt))
            {
                return true;
            }
        }

        return false;
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
    };
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
    var toolOptions = {
        paint: {close: false,
            closeAll: false},
        fill: {closeAll: false}
    };

    var paintWidth = 10;
    var eraseWidth = 10;

    // The following three objects hold per-mode delegate mouse event handlers
    // For instance, handleMouseDown['paint'] is a function to handle mouse-down events in
    // paint mode.
    var handleMouseDown = {};
    var handleMouseMove = {};
    var handleMouseUp = {};

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

    var brush;

    var isPainting = function()
    {
        return mouseState == 1;
    };

    var enterPaintingMode = function()
    {
        updateBrush();
    };

    var leavePaintingMode = function()
    {
        self.canvasLayer.canvas.isDrawingMode = false;
        proto_mouseCatcher.style.cursor = 'default';
        brush.opacity = 0;
        self.canvasLayer.canvas.renderAll();
    };

    var enterEraserMode = function()
    {
        updateBrush();
    };

    var leaveEraserMode = function()
    {
        self.canvasLayer.canvas.isDrawingMode = false;
        proto_mouseCatcher.style.cursor = 'default';
        brush.opacity = 0;
        self.canvasLayer.canvas.renderAll();
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

        brush = new fabric.Circle({top: 200,
            left: 200,
            radius: paintWidth / 2.0,
            fill: 'rgb(0,0,255)',
            opacity: 0});

        brush.setOriginX('center');
        brush.setOriginY('center');

        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.width = paintWidth;
        canvas.isDrawingMode = true;
        canvas.add(brush);

        canvas.on('path:created', function(e){
            if (currentArea != null)
            {
                self.handleCreatePath(e.path);
            }
        });

        self.stack.addLayer("AreaLayer", self.canvasLayer);
        self.stack.resize();

        self.canvasLayer.view.onmousedown = self.onmousedown;
        self.canvasLayer.view.onmouseup = self.onmouseup;

        canvas.renderAll();
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

    var readSVGAreaFromURL = function(id, areaIn, section)
    {
        var sliceUrl = '/sopnet/' + self.stack.getProject().id + '/stack/' + self.stack.id +
            '/polygon_slice/' + id + '.svg';

        var svgCall = function(objects, options)
        {
            var obj = fabric.util.groupSVGElements(objects, options);
            var area = self.getArea(areaIn);

            if (!area.hasObject(id))
            {
                obj.setColor(area.color);
                obj.setOpacity(area.opacity);

                self.registerDeserializedFabricObject(obj, area, id, section);

                self.canvasLayer.canvas.add(obj);

                area.updatePosition(self.stack.screenPosition(), self.stack.scale);
            }
        };

        fabric.loadSVGFromURL(sliceUrl, svgCall);
    };

    var removeTrace = function(traceId, areaId)
    {
        var area = self.getArea(areaId);
        var obj = area.removeObject(traceId);
        if (obj)
        {
            self.canvasLayer.canvas.remove(obj);
        }
    };

    var traceCallback = function(data)
    {
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
            growlAlert('Error', 'Problem retrieving trace. See console');
        }
        else
        {
            var tracesIn = data.slices;
            var tracesOut = data.replace_slices;
            var areasIn = data.assemblies;
            var idx;

            for (idx = 0; idx < areasIn.length; ++idx)
            {
                self.getOrCreateArea(areasIn[idx]);
            }

            for (idx = 0; idx < tracesIn.length; ++idx)
            {
                readSVGAreaFromURL(tracesIn[idx].id,
                    tracesIn[idx].assembly_id, tracesIn[idx].section);
            }

            for (idx = 0; idx < tracesOut.length; ++idx)
            {
                removeTrace(tracesOut[idx].id, tracesOut[idx].assembly_id);
            }

        }
    };

    var updateBrush = function()
    {
        var canvas = self.canvasLayer.canvas;

        if (currentArea == null)
        {
            proto_mouseCatcher.style.cursor = 'default';
            brush.opacity = 0;
        }
        else if(toolMode == 'paint')
        {
            proto_mouseCatcher.style.cursor = 'none';

            canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
            canvas.freeDrawingBrush.width = paintWidth;
            canvas.isDrawingMode = true;
            canvas.freeDrawingBrush.fill = currentArea.color;

            brush.setRadius(paintWidth / 2.0);
            brush.fill = currentArea.color;
            brush.opacity = currentArea.opacity;
            brush.stroke = '';
            brush.bringToFront();

            self.canvasLayer.canvas.freeDrawingBrush.color = currentArea.color;
            self.canvasLayer.canvas.freeDrawingBrush.opacity = currentArea.opacity;
        }
        else if (toolMode == 'erase')
        {
            proto_mouseCatcher.style.cursor = 'none';

            var freeBrush = new fabric.PatternBrush(canvas);
            var texture = new Image();
            texture.src = django_url + 'static/widgets/themes/kde/hatch.png';

            freeBrush.source = texture;
            freeBrush.width = eraseWidth;

            canvas.isDrawingMode = true;
            canvas.freeDrawingBrush = freeBrush;

            brush.setRadius(eraseWidth / 2.0);
            brush.fill = '';
            brush.stroke = 'rgb(255,0,0)';
            brush.strokeWidth = 2;
            brush.opacity = 1.0;
            brush.bringToFront();
        }

        canvas.renderAll();
    };



    var setupMouseHandlers = function()
    {
        handleMouseDown['paint'] = function(e)
        {
            if (currentArea != null)
            {
                mouseState = 1;
                self.canvasLayer.canvas._onMouseDownInDrawingMode(e);
                return true;
            }
            else
            {
                return false;
            }
        };

        handleMouseDown['erase'] = handleMouseDown['paint'];

        handleMouseDown['select'] = function(e)
        {
            var areas = self.areasAtScreenPoint(e);

            if (areas.length == 1)
            {
                self.setCurrentArea(areas[0]);
                uiChange();
            }
            else if (areas.length > 1)
            {
                var areaNameSelect = $('<select name="area_name_select" size="' + areas.length + '"/>');

                for (var idx=0; idx < areas.length; ++idx)
                {
                    var area = areas[idx];
                    areaNameSelect.append('<option value="' + area.assemblyId +
                        '">' + area.name + '</option>');
                }

                var selectAreaDiv = $('<div/>').append(areaNameSelect);

                areaNameSelect.change(function(){
                    self.setArea(this.value);
                    uiChange();
                    $.unblockUI();
                });

                areaNameSelect.css({width: 300});

                $.blockUI({message: selectAreaDiv, css: {width: 300, top: e.offsetY,
                    left: e.offsetX}});
            }
        };

        handleMouseDown['fill'] = function(e)
        {
            var loc = {x: e.offsetX, y: e.offsetY};

            AreaServerModel.closeHole(self.stack, currentArea.assemblyId, loc,
                toolOptions['fill']['closeAll'], traceCallback);
        };

        handleMouseDown['stamp'] = function(e)
        {

        };

        handleMouseUp['paint'] = function(e)
        {
            if (isPainting())
            {
                self.canvasLayer.canvas._onMouseUpInDrawingMode(e);
                return true;
            }
            else
            {
                return false;
            }
        };

        handleMouseUp['erase'] = handleMouseUp['paint'];


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
        AreaServerModel.tracesInView(self.stack, traceCallback);
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
            self.redraw();
            return true;
        }
    }));

    this.setPaintWidth = function(w)
    {
        paintWidth = w;

        if (toolMode == 'paint')
        {
            updateBrush();
            self.canvasLayer.canvas.renderAll();
            self.canvasLayer.canvas.freeDrawingBrush.width = w;
        }
    };

    this.getPaintWidth = function()
    {
        return paintWidth;
    };

    this.setEraseWidth = function(w)
    {
        eraseWidth = w;

        if (toolMode == 'erase')
        {
            updateBrush();
            self.canvasLayer.canvas.renderAll();
            self.canvasLayer.canvas.freeDrawingBrush.width = w;
        }
    };

    this.getAreas = function()
    {
        return areas;
    };

    this.onmousemove = function(e)
    {
        // If this isn't here, then the Circle brush doesn't line up with the freedraw stroke.
        // I'm not sure why.
        var magicOffset = 4;

        brush.left = e.offsetX - magicOffset;
        brush.top = e.offsetY - magicOffset;

        if (brush.opacity > 0)
        {
            self.canvasLayer.canvas.renderAll();
        }

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
            if (handleMouseDown.hasOwnProperty(toolMode))
            {
                return handleMouseDown[toolMode](e);
            }
            else
            {
                return false;
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
        if (e.button == 0)
        {
            if (handleMouseUp.hasOwnProperty(toolMode))
            {
                return handleMouseUp[toolMode](e);
            }
            else
            {
                return false;
            }
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

    this.areasAtScreenPoint = function(e)
    {
        var fabricPoint = new fabric.Point(e.offsetX, e.offsetY);
        var ptAreas = [];

        for (var idx = 0; idx < areas.length; ++idx)
        {
            var area = areas[idx];
            if (area.containsPoint(fabricPoint))
            {
                ptAreas.push(area);
            }
        }

        return ptAreas;
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

        // For whatever reason, this doesn't want to work.
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

    this.handleCreatePath = function(obj)
    {
        if (toolMode == 'paint')
        {
            self.registerFreshFabricObject(obj);
        }
        else
        {
            self.eraseByPath(obj);
        }
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

        AreaServerModel.pushTrace(self.stack, paintWidth, area.assemblyId,
            objectContainer, toolOptions['paint'], traceCallback);
    };

    this.eraseByPath = function(obj, areaIn)
    {
        var area = self.getArea(areaIn);
        var objectContainer = new FabricObjectContainer(obj, self.stack.scale,
            self.stack.screenPosition(), self.stack.z, nextId++);
        area.addObjectContainer(objectContainer);

        AreaServerModel.erase(self.stack, eraseWidth, area.assemblyId, objectContainer,
            traceCallback);
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

            setupMouseHandlers();
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
            if (self.lastZ != currentZ())
            {
                self.fetchAreas();
                trimTraces();
            }

            self.cacheScreenParameters();

            for (var i = 0; i < areas.length; ++i)
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
        currentArea = self.getArea(area);
    };

    this.setColor = function(color)
    {
        if (currentArea != null)
        {
            currentArea.setColor(color);
            updateBrush();
        }
    };

    this.setOpacity = function(opacity)
    {
        if (currentArea != null)
        {
            currentArea.setOpacity(opacity);
            updateBrush();
        }
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

    /**
     * Set tool-specific options. These are defined by the toolOptions variable.
     *
     * @param mode - the tool mode for which to set the option. Currently only 'paint' and 'fill'
     *               are accepted.
     * @param option - the option to set, these may be:
     *   paint: close - set true to ignore holes in new traces.
     *          closeAll - set true to also remove holes in any resulting merges with existing
     *                     traces.
     *   fill: closeAll - set true to remove all holes from a clicked trace, false to remove only
     *                    a clicked hole.
     * @param value - true or false
     */
    this.setToolOption = function(mode, option, value)
    {
        if (toolOptions.hasOwnProperty(mode))
        {
            var opts = toolOptions[mode];
            if (opts.hasOwnProperty(option))
            {
                opts[option] = value;
                return;
            }
        }

        console.log('Could not find option for ' + mode + ', ' + option);
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

        updateBrush();
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
    enterModeFunctions['erase'] = enterEraserMode;
    leaveModeFunctions['erase'] = leaveEraserMode;

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

    g_AreaWidget = this;

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

        toolModeLabel.append('<h2>' + tool.modeToString() + nameStr + '</h2>');

        self.updateToolSelector();
        self.updatePropertyEditor();
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
    var autoFillCheckbox;

    this.addAction = function(action)
    {
        toolActions.push(action);
    };

    var setAutoClose = function()
    {
        if (this.checked)
        {
            $('#paint_close_option').css('display', 'block');
        }
        else
        {
            $('#paint_close_option').css('display', 'none');
        }

        tool.setToolOption('paint', 'close', this.checked);

        console.log(this.checked);
    };

    this.updateToolSelector = function()
    {
        toolboxOptionsDiv.html('');

        toolboxOptionsDiv.append(toolOptionDivs[tool.getMode()]);

    };

    var setPaintBrushSize = function()
    {
        tool.setPaintWidth(this.val);
    };

    var setEraserSize = function()
    {
        tool.setEraseWidth(this.val);
    };

    var setFillMode = function()
    {
        console.log(this.value);
    };

    var setPaintFillMode = function()
    {
        tool.setToolOption('paint', 'closeAll', this.value=='all');
        console.log(this.value);
    };

    var createPaintOptions = function()
    {
        // options div.
        var od = $('<div id="area_paint_options"/>');
        var sliderDiv = $('<div id="area_paint_size_slider" />');

        var brushSizeSlider  = new Slider(SLIDER_HORIZONTAL, true, 1, maxBrushSize, maxBrushSize,
            16, setPaintBrushSize);
        autoFillCheckbox = createCheckboxHelper('Automatically Close Holes', setAutoClose);

        var closeDiv = $('<div id="paint_close_option"</div>');

        var one = $('<input type="radio" name="area_paint_radio" id="area_paint_close_one"' +
            ' value="one">Close New Holes</input>');
        var all = $('<input type="radio" name="area_paint_radio" id="area_paint_close_all"' +
            ' value="all">Close All Holes</input>');

        one.change(setPaintFillMode);
        all.change(setPaintFillMode);
        one.prop('checked', true);

        closeDiv.css('display', 'none');
        closeDiv.append(one).append('<br>').append(all);

        sliderDiv.append('Brush Size').append('<br>');
        sliderDiv.append(brushSizeSlider.getView());
        sliderDiv.append(brushSizeSlider.getInputView());

        od.append(sliderDiv).append('<br>').append(autoFillCheckbox);
        od.append('<br>').append(closeDiv);



        return od;
    };

    var createEraseOptions = function()
    {
        // options div.
        var od = $('<div id="area_erase_options"/>');
        var sliderDiv = $('<div id="area_erase_size_slider" />');

        var brushSizeSlider  = new Slider(SLIDER_HORIZONTAL, true, 1, maxBrushSize, maxBrushSize,
            16, setEraserSize);

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
        var one = $('<input type="radio" name="area_close_radio" id="area_close_one"' +
            ' value="one">Close One Hole</input>');
        var all = $('<input type="radio" name="area_close_radio" id="area_close_all"' +
            ' value="all">Close All Holes</input>');

        one.change(setFillMode);
        all.change(setFillMode);
        one.prop('checked', true);

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
    this.updatePropertyEditor = function() {
        if (tool.getArea() == null)
        {
            $('#area_opacity_slider').css('display', 'none');
            $('#assembly_color_wheel').css('display', 'none');
            $('#area_setting_message').css('display', 'block');
            colorWheel.color(AreaServerModel.defaultColor);
            opacitySlider.setByValue(AreaServerModel.defaultOpacity * 100, true);
        }
        else
        {
            $('#area_opacity_slider').css('display', 'block');
            $('#assembly_color_wheel').css('display', 'block');
            $('#area_setting_message').css('display', 'none');
            colorWheel.color(tool.getArea().getColor());
            opacitySlider.setByValue(tool.getArea().getOpacity() * 100, true);
        }
    };

    /**
     * Set the opacity of tool.currentArea according to the opacity slider.
     */
    var setToolOpacity = function()
    {
        if (tool != null)
        {
            tool.setOpacity(opacitySlider.val / 100.0);
            AreaServerModel.pushProperties(tool.getArea(), tool.stack);
        }
    };

    /**
     * Set the color of tool.currentArea according to the colorwheel.
     */
    var setToolColor = function()
    {
        if (tool != null)
        {
            tool.setColor(colorWheel.color().hex);
        }
    };

    /**
     * Set the color of the current area according to the colorwheel and push the change to the
     * server.
     */
    var setToolColorAndSync = function()
    {
        if (tool != null)
        {
            setToolColor();
            AreaServerModel.pushProperties(tool.getArea(), tool.stack);
        }
    };

    var createOpacitySlider = function()
    {
        var sliderDiv = $('<div id="area_opacity_slider" />');
        opacitySlider  = new Slider(SLIDER_HORIZONTAL, true, 0, 100, 101,
            50, setToolOpacity);

        sliderDiv.append('Opacity').append('<br>');
        sliderDiv.append(opacitySlider.getView());
        sliderDiv.append(opacitySlider.getInputView());

        return sliderDiv;
    };

    var createColorWheel = function()
    {
        var cwDiv = $('<div id="assembly_color_wheel"/>');
        colorWheel = Raphael.colorwheel(cwDiv, 150);
        colorWheel.onchange(setToolColorAndSync());
        colorWheel.ondrag(function(){}, setToolColorAndSync());
        return cwDiv;
    };

    var createPropertyEditor = function()
    {
        var opacitySliderDiv = createOpacitySlider();
        var colorWheelDiv = createColorWheel();
        var selectMessageDiv = $('<div id="area_setting_message"/>').append('Please Select an Object');
        selectMessageDiv.css('display', 'none');

        var propertyEditorDiv = $('<div/>').append(opacitySliderDiv);
        propertyEditorDiv.append('<br>').append(colorWheelDiv);
        propertyEditorDiv.append('<br>').append(selectMessageDiv);

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
        self.redraw();
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