
import bpy

def update_action_list(self, context):
    items = []
    obj = context.active_object
    
    if obj and obj.animation_data:
        # Collect actions from NLA tracks
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    items.append((strip.action.name, strip.action.name, ''))
        
        # Also include the currently assigned action if not in NLA
        if obj.animation_data.action:
            act = obj.animation_data.action
            if not any(i[0] == act.name for i in items):
                items.append((act.name, act.name, ''))
                
    # If no actions found, return a dummy item to avoid errors
    if not items:
        return [("None", "None", "")]
        
    return items

class BakeAction_PT(bpy.types.Panel):
    bl_idname = "OBJECT_PT_bake_action"
    bl_label = "Bake Action"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Create the source action list
        row = layout.row()
        row.label(text="Source Action:")
        row.prop(context.scene, "source_action", text="")

        # Create the destination action list
        row = layout.row()
        row.label(text="Destination Action:")
        row.prop(context.scene, "destination_action", text="")

        # Create the bake button
        row = layout.row()
        row.operator("animation.bake_action", text="Bake Action")

class BakeAction_OT(bpy.types.Operator):
    bl_idname = "animation.bake_action"
    bl_label = "Bake Action"

    def execute(self, context):
        # Get the active object
        obj = context.active_object

        # Set the active action to the source action
        source_action = bpy.data.actions[context.scene.source_action]

        # Set the selected action to the destination action
        destination_action = bpy.data.actions[context.scene.destination_action]
        
        #check if source and destination actions are the same
        if source_action == destination_action or source_action == None or destination_action == None:
            print("Error: please select source and destination actions that are not similar!")
            return {'CANCELLED'}
        
        # Loop through each f-curve of the selected action
        for fcurve in destination_action.fcurves:
            # check if there are similar f-curve in active action
            active_fcurve = source_action.fcurves.find(fcurve.data_path, index=fcurve.array_index)
            if not active_fcurve:
                continue
            # Loop over each keyframe of the f-curve
            for keyframe in fcurve.keyframe_points:
                # Calculate the offset between the two keyframes
                active_value = active_fcurve.evaluate(keyframe.co[0])
                offset = active_value - keyframe.co[1]
                # Offset the selected action's keyframe parameters
                keyframe.co[1] += offset
                keyframe.handle_left[1] += offset
                keyframe.handle_right[1] += offset

        return {'FINISHED'}

classes = (
            BakeAction_OT,
            BakeAction_PT,
        )

def register():
    bpy.types.Scene.source_action = bpy.props.EnumProperty(
        items=update_action_list, 
        name="Source Action"
    )
    bpy.types.Scene.destination_action = bpy.props.EnumProperty(
        items=update_action_list, 
        name="Destination Action"
    )
    for my_class in classes:
        bpy.utils.register_class(my_class)
    
   

def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)
        
    del bpy.types.Scene.source_action
    del bpy.types.Scene.destination_action

if __name__ == "__main__":
    register()
