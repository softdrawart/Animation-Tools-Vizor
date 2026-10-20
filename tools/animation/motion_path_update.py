bl_info = {
    "name": "Graph Editor Motion Trail Updater",
    "author": "Assistant",
    "version": (1, 3, 0),
    "blender": (4, 0, 0),
    "location": "Graph Editor > Sidebar > Motion Trail",
    "description": "Auto-updates motion trails in real-time when modifying F-Curves.",
    "category": "Animation",
}

import bpy

# Global flag to track when animation data changes
_needs_update = False

@bpy.app.handlers.persistent
def graph_depsgraph_handler(scene, depsgraph):
    """Fires every time something in the scene updates (like dragging an F-Curve)."""
    global _needs_update
    if depsgraph.updates:
        _needs_update = True


def get_view3d_override(context):
    """Helper function to find a 3D Viewport and return an override dictionary."""
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {"window": window, "area": area, "region": region}
    return None


class GraphMotionTrailProps(bpy.types.PropertyGroup):
    is_running: bpy.props.BoolProperty(
        name="Operator Running",
        default=False
    )
    update_only_on_release: bpy.props.BoolProperty(
        name="Update Only on Release",
        description="If enabled, updates only after you release the mouse to save performance. If disabled, updates continuously in real-time while dragging.",
        default=False 
    )


class GRAPH_OT_motion_path_calculate(bpy.types.Operator):
    bl_idname = "graph.motion_path_calculate"
    bl_label = "Calculate Motion Paths"
    bl_description = "Calculate motion paths for the selected bones or objects"
    
    def invoke(self, context, event):
        override = get_view3d_override(context)
        if not override:
            self.report({'WARNING'}, "No 3D Viewport found")
            return {'CANCELLED'}
            
        with context.temp_override(**override):
            if context.active_object and context.active_object.mode == 'POSE':
                return bpy.ops.pose.paths_calculate('INVOKE_DEFAULT')
            else:
                return bpy.ops.object.paths_calculate('INVOKE_DEFAULT')


class GRAPH_OT_motion_path_update_all(bpy.types.Operator):
    bl_idname = "graph.motion_path_update_all"
    bl_label = "Update All Paths"
    bl_description = "Update visible motion paths"
    
    def execute(self, context):
        override = get_view3d_override(context)
        if not override:
            return {'CANCELLED'}
            
        with context.temp_override(**override):
            if context.active_object and context.active_object.mode == 'POSE':
                bpy.ops.object.paths_update_visible()
            else:
                bpy.ops.object.paths_update_visible()
        return {'FINISHED'}


class GRAPH_OT_motion_path_clear(bpy.types.Operator):
    bl_idname = "graph.motion_path_clear"
    bl_label = "Clear Motion Paths"
    bl_description = "Clear motion paths for the selected bones or objects"
    
    def execute(self, context):
        override = get_view3d_override(context)
        if not override:
            return {'CANCELLED'}
            
        with context.temp_override(**override):
            if context.active_object and context.active_object.mode == 'POSE':
                bpy.ops.pose.paths_clear()
            else:
                bpy.ops.object.paths_clear()
        return {'FINISHED'}


class GRAPH_OT_motion_trail_modal(bpy.types.Operator):
    bl_idname = "graph.motion_trail_auto_update"
    bl_label = "Motion Trail Auto Update"
    bl_description = "Listen for F-Curve edits and update the motion trail"
    
    _timer = None

    def modal(self, context, event):
        global _needs_update
        props = context.window_manager.graph_mt_props

        if not props.is_running:
            self.cancel(context)
            return {'FINISHED'}

        is_release_event = (
            (event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'RELEASE') or
            (event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'} and event.value == 'PRESS')
        )

        if is_release_event:
            if props.update_only_on_release and _needs_update:
                self.trigger_update(context)
                _needs_update = False

        elif event.type == 'TIMER':
            if not props.update_only_on_release and _needs_update:
                self.trigger_update(context)
                _needs_update = False

        return {'PASS_THROUGH'}

    def trigger_update(self, context):
        try:
            if hasattr(context.window_manager, "motion_trail"):
                context.window_manager.motion_trail.force_update = True
        except AttributeError:
            pass

        obj = context.active_object
        if obj:
            override = get_view3d_override(context)
            if override:
                with context.temp_override(**override):
                    try:
                        if obj.mode == 'POSE':
                            bpy.ops.object.paths_update_visible()
                        else:
                            bpy.ops.object.paths_update_visible()
                    except RuntimeError:
                        pass

    def execute(self, context):
        props = context.window_manager.graph_mt_props
        
        if props.is_running:
            self.cancel(context)
            return {'FINISHED'}
        else:
            props.is_running = True
            if graph_depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.append(graph_depsgraph_handler)
                
            self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
            
        if graph_depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(graph_depsgraph_handler)
            
        context.window_manager.graph_mt_props.is_running = False


class GRAPH_PT_motion_trail_panel(bpy.types.Panel):
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Motion Trail"
    bl_label = "Motion Trail Trigger"

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.graph_mt_props
        obj = context.active_object

        # 1. Action Buttons (Calculate, Update, Clear)
        col = layout.column(align=True)
        if obj:
            is_pose = (obj.mode == 'POSE')
            icon_calc = 'BONE_DATA' if is_pose else 'OBJECT_DATA'
            
            col.operator(GRAPH_OT_motion_path_calculate.bl_idname, text="Calculate...", icon=icon_calc)
            
            row = col.row(align=True)
            row.operator(GRAPH_OT_motion_path_update_all.bl_idname, text="Update All Paths", icon='WORLD_DATA')
            row.operator(GRAPH_OT_motion_path_clear.bl_idname, text="", icon='X')

        layout.separator()

        # 2. Auto-Update Settings
        col = layout.column(align=True)
        if props.is_running:
            col.operator(GRAPH_OT_motion_trail_modal.bl_idname, text="Stop Auto-Update", icon='CANCEL')
        else:
            col.operator(GRAPH_OT_motion_trail_modal.bl_idname, text="Start Auto-Update", icon='PLAY')

        layout.separator()
        
        col = layout.column()
        col.active = props.is_running 
        col.prop(props, "update_only_on_release")


classes = (
    GraphMotionTrailProps,
    GRAPH_OT_motion_path_calculate,
    GRAPH_OT_motion_path_update_all,
    GRAPH_OT_motion_path_clear,
    GRAPH_OT_motion_trail_modal,
    GRAPH_PT_motion_trail_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.WindowManager.graph_mt_props = bpy.props.PointerProperty(type=GraphMotionTrailProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.WindowManager.graph_mt_props
    
    if graph_depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(graph_depsgraph_handler)

if __name__ == "__main__":
    register()