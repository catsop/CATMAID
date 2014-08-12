
function AreaTool()
{
  this.prototype = new Navigator();

  this.toolname = "Area Tracing Tool";

  var self = this;

  this.register = function(parentStack)
  {
    self.stack = parentStack;

    $("#toolbar_area")[0].style_display = "block";

    self.prototype.register( parentStack, "area_tool_button");

    return;
  }

  this.unregister = function()
  {
    self.prototype.destroy( "area_tool_button" );
    return;
  }
}
