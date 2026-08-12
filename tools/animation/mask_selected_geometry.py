import bpy

def get_related_meshes(armature):
    meshes = set()
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == armature:
                    meshes.add(obj)
                    break
            if obj.parent == armature:
                meshes.add(obj)
    return list(meshes)

def is_controlled_by(bone, target_name, armature, visited=None):
    """Recursively checks if a bone is controlled by a target bone via constraints or parenting."""
    if visited is None:
        visited = set()
        
    if bone.name in visited:
        return False
        
    visited.add(bone.name)
    
    # 1. Check direct parent
    if bone.parent and bone.parent.name == target_name:
        return True
        
    # 2. Check direct constraints
    for c in bone.constraints:
        target_obj = getattr(c, 'target', None)
        if target_obj and target_obj != armature:
            continue  # Skip constraints targeting objects outside the current armature
            
        subtarget = getattr(c, 'subtarget', None)
        if subtarget == target_name:
            return True
            
    # 3. Recursive trace up parent hierarchy
    if bone.parent and is_controlled_by(bone.parent, target_name, armature, visited):
        return True
        
    # 4. Recursive trace up constraint hierarchy (MCH or ORG bones)
    for c in bone.constraints:
        target_obj = getattr(c, 'target', None)
        if target_obj and target_obj != armature:
            continue
            
        subtarget = getattr(c, 'subtarget', None)
        if subtarget and subtarget in armature.pose.bones:
            if is_controlled_by(armature.pose.bones[subtarget], target_name, armature, visited):
                return True
                
    return False

def get_actual_deform_bone_names(armature, selected_pose_bones):
    """Finds deformation bones corresponding to the selected (potentially non-deform) bones."""
    deform_names = set()
    
    if not selected_pose_bones:
        return list(deform_names)
        
    all_deform_bones = [b for b in armature.pose.bones if b.bone.use_deform]
    
    for p_bone in selected_pose_bones:
        # If the selected bone is already a deform bone
        if p_bone.bone.use_deform:
            deform_names.add(p_bone.name)
        
        # Method 1: Check for 'DEF-' prefix (Simplest way for Rigify)
        def_name = "DEF-" + p_bone.name
        # Strip out IK/FK identifiers
        if "_fk" in def_name or "_ik" in def_name:
            def_name = def_name.replace("_fk", "").replace("_ik", "")

        if def_name in armature.pose.bones and armature.pose.bones[def_name].bone.use_deform:
            deform_names.add(def_name)
            continue  # Skip further checks if DEF- bone is found
            
        # Method 2: Traverse hierarchy to find connected deform bones
        for def_bone in all_deform_bones:
            if def_bone.name not in deform_names:
                if is_controlled_by(def_bone, p_bone.name, armature):
                    deform_names.add(def_bone.name)
                    
    return list(deform_names)

class ANIM_OT_ModifySoloMask(bpy.types.Operator):
    """Add or Remove bones from the existing Solo Mask"""
    bl_idname = "anim.modify_solo_mask"
    bl_label = "Modify Solo Mask"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: bpy.props.EnumProperty(items=[('ADD', 'Add', ''), ('REMOVE', 'Remove', '')])

    def execute(self, context):
        armature = context.active_object
        if not context.selected_pose_bones: return {'CANCELLED'}
        
        original_bones = [b.name for b in context.selected_pose_bones]
        deform_bones = get_actual_deform_bone_names(armature, context.selected_pose_bones)
        
        # Combine lists to ensure direct mesh parenting to control bones isn't broken
        selected_bones = list(set(original_bones + deform_bones))

        for obj in get_related_meshes(armature):
            mask_group = obj.vertex_groups.get("Solo_Mask")
            if not mask_group: continue 

            # Get indices for selected bones
            bone_indices = [obj.vertex_groups[b].index for b in selected_bones if b in obj.vertex_groups]
            
            # Identify vertices to change
            target_indices = []
            for vert in obj.data.vertices:
                if any(g.group in bone_indices and g.weight > 0.001 for g in vert.groups):
                    target_indices.append(vert.index)
            
            # Handle Parenting check
            if obj.parent_type == 'BONE' and obj.parent_bone in selected_bones:
                target_indices = [v.index for v in obj.data.vertices]

            if target_indices:
                mask_group.add(target_indices, 1.0, 'ADD' if self.action == 'ADD' else 'SUBTRACT')
        
        return {'FINISHED'}

class ANIM_OT_SoloBoneGeometry(bpy.types.Operator):
    """Solo geometry (Reset and set to selection)"""
    bl_idname = "anim.solo_bone_geometry"
    bl_label = "Solo Selected Bone Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.active_object
        if not context.selected_pose_bones: return {'CANCELLED'}
        
        original_bones = [b.name for b in context.selected_pose_bones]
        deform_bones = get_actual_deform_bone_names(armature, context.selected_pose_bones)
        selected_bone_names = list(set(original_bones + deform_bones))
        
        for obj in get_related_meshes(armature):
            mask_group = obj.vertex_groups.get("Solo_Mask")
            if mask_group: obj.vertex_groups.remove(mask_group)
            mask_group = obj.vertex_groups.new(name="Solo_Mask")

            bone_group_indices = [obj.vertex_groups[b].index for b in selected_bone_names if b in obj.vertex_groups]
            
            for vert in obj.data.vertices:
                if any(g.group in bone_group_indices and g.weight > 0.001 for g in vert.groups):
                    mask_group.add([vert.index], 1.0, 'REPLACE')

            if obj.parent_type == 'BONE' and obj.parent_bone in selected_bone_names:
                mask_group.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')

            if not obj.modifiers.get("Solo_Mask_Modifier"):
                mod = obj.modifiers.new(name="Solo_Mask_Modifier", type='MASK')
                mod.vertex_group = "Solo_Mask"
        return {'FINISHED'}

class ANIM_OT_RemoveSoloMask(bpy.types.Operator):
    bl_idname = "anim.remove_solo_mask"
    bl_label = "Remove Mask & Cleanup"
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if obj.modifiers.get("Solo_Mask_Modifier"): obj.modifiers.remove(obj.modifiers["Solo_Mask_Modifier"])
                if obj.vertex_groups.get("Solo_Mask"): obj.vertex_groups.remove(obj.vertex_groups["Solo_Mask"])
        return {'FINISHED'}

class VIEW3D_PT_BoneSoloPanel(bpy.types.Panel):
    bl_label = "Bone Geometry Solo"
    bl_idname = "VIEW3D_PT_bone_solo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("anim.solo_bone_geometry", text="Solo Selected", icon='HIDE_OFF')
        col.separator()
        row = col.row(align=True)
        op_add = row.operator("anim.modify_solo_mask", text="Add to Solo", icon='ADD')
        op_add.action = 'ADD'
        op_sub = row.operator("anim.modify_solo_mask", text="Remove from Solo", icon='REMOVE')
        op_sub.action = 'REMOVE'
        col.separator()
        col.operator("anim.remove_solo_mask", text="Cleanup", icon='TRASH')

classes = (
    ANIM_OT_ModifySoloMask,
    ANIM_OT_SoloBoneGeometry,
    ANIM_OT_RemoveSoloMask,
    VIEW3D_PT_BoneSoloPanel
)

def register():
    for my_class in classes:
        bpy.utils.register_class(my_class)

def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)

if __name__ == "__main__":
    register()