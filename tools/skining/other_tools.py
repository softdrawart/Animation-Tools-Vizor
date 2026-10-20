import bpy
import bmesh
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
            bone = armature_obj.pose.bones.get(old_group_name)
            def_bone = armature_obj.data.bones.get(old_group_name)
            if not bone:
                continue
                
            # Must be a deformation bone
            if not def_bone.use_deform:
                continue
                
            # If 'all' is False, only process selected bones
            if not self.all and bone and not bone.select:
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

class MESH_OT_selected_vertices_bisect_mirror_weights(bpy.types.Operator):
    """Mirror weights automatically to the selected side using a bisected duplicate"""
    bl_idname = "mesh.selected_vertices_bisect_mirror_weights"
    bl_label = "Selected Vertices Bisect Mirror Weights"
    bl_options = {'REGISTER', 'UNDO'}

    mirror_axis: bpy.props.EnumProperty(
        name="Mirror Axis",
        description="Axis to mirror and bisect across",
        items=[
            ('X', "X", "Mirror across X axis"),
            ('Y', "Y", "Mirror across Y axis"),
            ('Z', "Z", "Mirror across Z axis"),
        ],
        default='X'
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        orig_obj = context.active_object
        scene = context.scene

        # 1. Evaluate vertex selection sides using bmesh
        bm = bmesh.from_edit_mesh(orig_obj.data)
        
        axis_index = {'X': 0, 'Y': 1, 'Z': 2}[self.mirror_axis]
        has_positive = False
        has_negative = False
        
        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'ERROR'}, "No vertices selected.")
            return {'CANCELLED'}

        for v in selected_verts:
            val = v.co[axis_index]
            if val > 0.0001:
                has_positive = True
            elif val < -0.0001:
                has_negative = True

        if has_positive and has_negative:
            self.report({'ERROR'}, "Both sides selected! Please select vertices on only one side of the axis.")
            return {'CANCELLED'}
        
        if not has_positive and not has_negative:
            self.report({'ERROR'}, "Selected vertices are perfectly centered on the mirror axis.")
            return {'CANCELLED'}

        # Blender mirrors + to - by default. 
        # If selection is positive, we need to copy from negative, so we must flip the bisect.
        auto_flip = has_positive 

        # 2. Switch to Object Mode to safely duplicate
        bpy.ops.object.mode_set(mode='OBJECT')

        # 3. Duplicate the active mesh object
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj
        
        bpy.ops.object.duplicate(linked=False)
        dup_obj = context.active_object
        dup_obj.name = orig_obj.name + "_Bisect_Temp"

        # 4. Add and configure the Mirror modifier
        mod = dup_obj.modifiers.new(name="WeightBisectMirror", type='MIRROR')
        
        mod.use_axis[0] = (self.mirror_axis == 'X')
        mod.use_axis[1] = (self.mirror_axis == 'Y')
        mod.use_axis[2] = (self.mirror_axis == 'Z')
        
        mod.use_bisect_axis[0] = (self.mirror_axis == 'X')
        mod.use_bisect_axis[1] = (self.mirror_axis == 'Y')
        mod.use_bisect_axis[2] = (self.mirror_axis == 'Z')
        
        mod.use_bisect_flip_axis[0] = (self.mirror_axis == 'X' and auto_flip)
        mod.use_bisect_flip_axis[1] = (self.mirror_axis == 'Y' and auto_flip)
        mod.use_bisect_flip_axis[2] = (self.mirror_axis == 'Z' and auto_flip)
        
        mod.use_clip = True

        # 5. Apply the Mirror modifier
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # 6. Setup for the Proximity Weight Transfer
        prev_source_obj = scene.weight_source_object
        scene.weight_source_object = dup_obj

        # Target original object
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj
        
        # Switch back to Edit Mode (restores exact vertex selection)
        bpy.ops.object.mode_set(mode='EDIT')

        # 7. Call the existing proximity transfer operator
        try:
            bpy.ops.mesh.proximity_weight_transfer()
        except Exception as e:
            self.report({'ERROR'}, f"Weight transfer failed: {str(e)}")

        # 8. Cleanup operations
        bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        dup_obj.select_set(True)
        bpy.ops.object.delete()

        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj
        scene.weight_source_object = prev_source_obj

        bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, f"Weights mirrored automatically (Flip required: {auto_flip}).")
        return {'FINISHED'}

class MESH_RemoveNonDeformVGroups_OT_VIZOR(bpy.types.Operator):
    """Remove all vertex groups not associated with a deforming bone in the armature(s)"""
    bl_idname = "mesh.remove_non_deform_vgroups"
    bl_label = "Remove Non-Deform Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        # Filter selection to meshes only
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        total_removed_count = 0
        processed_objects_count = 0

        for obj in selected_meshes:
            # 1. Find all armature modifiers for THIS specific object
            arm_modifiers = [m for m in obj.modifiers if m.type == 'ARMATURE' and m.object]
            
            # Skip this object if it has no armatures assigned
            if not arm_modifiers:
                continue
                
            # 2. Build a set of all valid deform bone names from all attached armatures
            deform_bone_names = set()
            for mod in arm_modifiers:
                arm_obj = mod.object
                for bone in arm_obj.data.bones:
                    if bone.use_deform:
                        deform_bone_names.add(bone.name)

            # 3. Identify vertex groups on this mesh that are NOT in the deform set
            vgroups_to_remove = [vg for vg in obj.vertex_groups if vg.name not in deform_bone_names]

            # 4. Remove the groups
            if vgroups_to_remove:
                processed_objects_count += 1
                for vg in vgroups_to_remove:
                    obj.vertex_groups.remove(vg)
                    total_removed_count += 1
            
        # Final report
        self.report(
            {'INFO'}, 
            f"Processed {processed_objects_count} objects. Removed {total_removed_count} vertex groups."
        )
        
        return {'FINISHED'}
class CLEAR_EMPTY_WEIGHTS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "skin.clear_empty_weights"
    bl_label = "clear empty weights from object"
    bl_description = "clear empty weights from object"
    bl_options = {'REGISTER', 'UNDO'}

    threshold: bpy.props.FloatProperty(default=0, min=0, max=1)

    def find_weights(self, obj):
        maxWeight = {}
        for i in obj.vertex_groups:
            maxWeight[i.index] = 0

        for v in obj.data.vertices:
            for g in v.groups:
                gn = g.group
                w = obj.vertex_groups[gn].weight(v.index)
                if (maxWeight.get(gn) is None or w>maxWeight[gn]):
                    maxWeight[gn] = w
        return maxWeight
    def remove_empty_weights(self, obj):
        maxWeight = self.find_weights(obj)
        # fix bug pointed out by user2859
        ka = []
        ka.extend(maxWeight.keys())
        ka.sort(key=lambda gn: -gn)
        print (ka)
        for gn in ka:
            if maxWeight[gn]<=self.threshold:
                print ("delete %d"%gn)
                obj.vertex_groups.remove(obj.vertex_groups[gn]) # actually remove the group

    def execute(self, context):
        obj = context.active_object
        for obj in [obj for obj in context.selected_objects if obj.type=='MESH']:
            self.remove_empty_weights(obj)
        return {'FINISHED'}

class VIEW3D_PT_other_tools(bpy.types.Panel):
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
        layout.operator("mesh.selected_vertices_bisect_mirror_weights", text="Bisect Mirror Weights", icon='MOD_MIRROR')
        layout.operator("mesh.remove_non_deform_vgroups", text="Remove Non-Deform Vertex Groups", icon='X')
        layout.operator("skin.clear_empty_weights", text="Clear Empty Weights", icon='X')

# List of classes to register
classes = (
    MIRROR_WEIGHTS_OT_VIZOR,
    CLEAR_EMPTY_WEIGHTS_OT_VIZOR,
    VIEW3D_PT_other_tools,
    MESH_RemoveNonDeformVGroups_OT_VIZOR,
    MESH_OT_selected_vertices_bisect_mirror_weights
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

if __name__ == "__main__":
    register()