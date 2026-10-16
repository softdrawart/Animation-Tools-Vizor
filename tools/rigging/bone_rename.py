import bpy

class POSE_OT_rename_rigify_type(bpy.types.Operator):
    """Update rigify_type for selected bones based on the chosen method"""
    bl_idname = "pose.rename_rigify_type"
    bl_label = "Update Rigify Type"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Checks if we are in POSE mode and have bones selected
        return (context.active_object and 
                context.active_object.type == 'ARMATURE' and 
                context.mode == 'POSE' and 
                len(context.selected_pose_bones) > 0)

    def execute(self, context):
        scene = context.scene
        method = scene.rigify_rename_method

        for bone in context.selected_pose_bones:
            # Check if the bone has the custom property 'rigify_type'
            if "rigify_type" in bone.keys():
                current_type = bone["rigify_type"]
                new_type = current_type
                
                # Execute logic based on the selected dropdown method
                if method == 'FIND_REPLACE':
                    find_str = scene.rigify_find_str
                    replace_str = scene.rigify_replace_str
                    if find_str and find_str in new_type:
                        new_type = new_type.replace(find_str, replace_str)
                        
                elif method == 'PREFIX':
                    prefix_str = scene.rigify_prefix_str
                    if prefix_str:
                        new_type = prefix_str + new_type
                        
                elif method == 'SUFFIX':
                    suffix_str = scene.rigify_suffix_str
                    if suffix_str:
                        new_type = new_type + suffix_str
                
                # Apply changes if modified
                if current_type != new_type:
                    bone["rigify_type"] = new_type
                    self.report({'INFO'}, f"Updated {bone.name}: {current_type} -> {new_type}")
            else:
                print(f"{bone.name} does not have rigify_type")

        return {'FINISHED'}

class VIEW3D_PT_rigify_renamer_panel(bpy.types.Panel):
    """Creates a Panel in the 3D View Sidebar"""
    bl_label = "Rigify Type Renamer"
    bl_idname = "VIEW3D_PT_rigify_renamer_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Rigging'

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Dropdown to choose the method
        layout.prop(scene, "rigify_rename_method", text="")
        layout.separator()

        # Conditionally show properties based on the selected method
        method = scene.rigify_rename_method
        
        if method == 'FIND_REPLACE':
            layout.prop(scene, "rigify_find_str", text="Find")
            layout.prop(scene, "rigify_replace_str", text="Replace")
        elif method == 'PREFIX':
            layout.prop(scene, "rigify_prefix_str", text="Prefix")
        elif method == 'SUFFIX':
            layout.prop(scene, "rigify_suffix_str", text="Suffix")
        
        layout.separator()
        
        # Operator button
        layout.operator(POSE_OT_rename_rigify_type.bl_idname)

classes = (
    POSE_OT_rename_rigify_type,
    VIEW3D_PT_rigify_renamer_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    # Dropdown property
    bpy.types.Scene.rigify_rename_method = bpy.props.EnumProperty(
        name="Method",
        description="Choose how to modify the rigify_type property",
        items=[
            ('FIND_REPLACE', "Find & Replace", "Find a string and replace it"),
            ('PREFIX', "Add Prefix", "Add a string to the beginning"),
            ('SUFFIX', "Add Suffix", "Add a string to the end"),
        ],
        default='FIND_REPLACE'
    )
        
    bpy.types.Scene.rigify_find_str = bpy.props.StringProperty(
        name="Find",
        description="String to search for in rigify_type",
        default="game."
    )
    bpy.types.Scene.rigify_replace_str = bpy.props.StringProperty(
        name="Replace",
        description="String to replace it with",
        default=""
    )
    bpy.types.Scene.rigify_prefix_str = bpy.props.StringProperty(
        name="Prefix",
        description="String to prepend to rigify_type",
        default=""
    )
    bpy.types.Scene.rigify_suffix_str = bpy.props.StringProperty(
        name="Suffix",
        description="String to append to rigify_type",
        default=""
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.rigify_rename_method
    del bpy.types.Scene.rigify_find_str
    del bpy.types.Scene.rigify_replace_str
    del bpy.types.Scene.rigify_prefix_str
    del bpy.types.Scene.rigify_suffix_str

if __name__ == "__main__":
    register()