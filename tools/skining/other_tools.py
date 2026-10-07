import bpy

class MIRROR_WEIGHTS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.mirror_skin_weights"
    bl_label = "mirror all skin weights"
    bl_description = "mirror all skin weights"
    bl_options = {'REGISTER', 'UNDO'}
    
    all: bpy.props.BoolProperty(
        name="All Deform Bones",
        description="If True, mirrors all deformation bones. If False, only selected deformation bones",
        default=False
    )
    
    override: bpy.props.BoolProperty(
        name="Override Existing",
        description="If True, removes existing mirrored weights and replaces them",
        default=False
    )
    @classmethod
    def poll(cls, context):
        # Ensure the operator only runs in Weight Paint mode with a valid mesh and armature
        if context.mode != 'PAINT_WEIGHT':
            return False
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            return False
        
        armature_obj = mesh.find_armature()
        if not armature_obj:
            return False
        
        return True
    
    def execute(self, context):
        # Get the active object
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Selected object is not a mesh. Aborting.")
            return {'CANCELLED'}

        # Find the armature linked to this mesh to check for bone data
        armature_obj = None
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                armature_obj = mod.object
                break
                
        if not armature_obj:
            self.report({'WARNING'}, "No Armature modifier found on the active mesh.")
            return {'CANCELLED'}

        vertex_group_names = [group.name for group in obj.vertex_groups]

        # Loop through the vertex group names
        for old_group_name in vertex_group_names:
            # Check if this vertex group corresponds to a bone in the armature
            bone = armature_obj.data.bones.get(old_group_name)
            if not bone:
                continue
                
            # Must be a deformation bone
            if not bone.use_deform:
                continue
                
            # If 'all' is False, only process selected bones
            if not self.all and not bone.select:
                continue

            new_group_name = None
            
            # Check for naming conventions and define the target mirrored name
            if '.L' in old_group_name:
                new_group_name = old_group_name.replace('.L', '.R')
            elif '.R' in old_group_name:
                new_group_name = old_group_name.replace('.R', '.L')
            elif 'Left' in old_group_name:
                new_group_name = old_group_name.replace('Left', 'Right')
            elif 'Right' in old_group_name:
                new_group_name = old_group_name.replace('Right', 'Left')
            else:
                continue
                
            # Check if the target mirrored group already exists
            existing_group = obj.vertex_groups.get(new_group_name)
            if existing_group:
                if self.override:
                    # Remove the existing group so it can be replaced cleanly
                    obj.vertex_groups.remove(existing_group)
                else:
                    # Skip mirroring this group if override is False
                    continue
            
            # Ensure the source group still exists
            if not obj.vertex_groups.get(old_group_name):
                continue
                
            # Set the current vertex group as active
            bpy.ops.object.vertex_group_set_active(group=old_group_name)

            # Copy the current vertex group
            bpy.ops.object.vertex_group_copy()

            # Mirror the vertex group using topology
            bpy.ops.object.vertex_group_mirror(use_topology=False)

            # Rename the new mirrored vertex group
            context.active_object.vertex_groups.active.name = new_group_name
            print(f"Weight group {new_group_name} mirrored and duplicated.")
            
        return {'FINISHED'}

class VIEW3D_PT_mirror_weights(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport UI sidebar"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Skinning'
    bl_label = "Skin Weights Tools"

    def draw(self, context):
        layout = self.layout
        
        # --- NATIVE VERTEX WEIGHTS PANEL ---
        layout.label(text="Vertex Weights:")
        row = layout.row()
        row.operator("object.vertex_weight_normalize_active_vertex", text="Normalize")
        row.operator("object.vertex_weight_copy", text="Copy")
        layout.separator()

        # --- CUSTOM TOOLS ---
        layout.label(text="Custom Tools:")
        layout.operator("animation.mirror_skin_weights", text="Mirror Skin Weights", icon='MOD_MIRROR')


# List of classes to register
classes = (
    MIRROR_WEIGHTS_OT_VIZOR,
    VIEW3D_PT_mirror_weights,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()