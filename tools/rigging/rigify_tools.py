
import bpy

class ARMATURE_OT_transfer_rigify_action_slots(bpy.types.Operator):
    """Transfer rigify action slots from selected source armature to active target armature"""
    bl_idname = "armature.transfer_rigify_action_slots"
    bl_label = "Transfer Rigify Action Slots"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Ensure context mode is object, we have an active object, 
        # and exactly two armatures are involved (one active, one selected)
        if context.mode != 'OBJECT':
            return False
        
        active = context.active_object
        selected = context.selected_objects
        
        if not active or active.type != 'ARMY' and active.type != 'ARMATURE':
            # Check for armature type explicitly
            pass
            
        if active and active.type == 'ARMATURE':
            armature_selected = [obj for obj in selected if obj.type == 'ARMATURE']
            # We need 2 armatures: the active target and 1 other selected source
            if len(armature_selected) == 2 and active in armature_selected:
                return True
                
        return False

    def execute(self, context):
        target_obj = context.active_object
        selected_objs = context.selected_objects
        
        # Identify source armature (the selected one that is NOT the active object)
        source_objs = [obj for obj in selected_objs if obj.type == 'ARMATURE' and obj != target_obj]
        
        if not source_objs:
            self.report({'ERROR'}, "No source armature found in selection.")
            return {'CANCELLED'}
            
        source_obj = source_objs[0]
        
        src_data = source_obj.data
        tgt_data = target_obj.data
        
        if not hasattr(src_data, "rigify_action_slots"):
            self.report({'ERROR'}, f"Source armature '{source_obj.name}' does not have 'rigify_action_slots'.")
            return {'CANCELLED'}
            
        if not hasattr(tgt_data, "rigify_action_slots"):
            self.report({'ERROR'}, f"Target armature '{target_obj.name}' does not have 'rigify_action_slots'.")
            return {'CANCELLED'}
            
        # Clear existing slots on target to mirror source completely, or clear/add. 
        # Usually, copying means replacing or appending. Let's clear target slots first or reuse.
        # Since collections usually have clear or we can loop through and remove/add:
        tgt_slots = tgt_data.rigify_action_slots
        src_slots = src_data.rigify_action_slots
        
        # Clear target slots safely if a clear method exists, otherwise pop or clear loop
        try:
            tgt_slots.clear()
        except AttributeError:
            # Fallback if clear() isn't directly exposed on this collection property
            while len(tgt_slots) > 0:
                tgt_slots.remove(0)
                
        # List of attributes to copy over from each slot
        slot_attributes = [
            "name",
            "action",
            "enabled",
            "frame_start",
            "frame_end",
            "is_corrective",
            "keyed_bone_names",
            "subtarget",
            "symmetrical",
            "target_space",
            "trans_max",
            "trans_min",
            "transform_channel",
            "trigger_action_a",
            "trigger_action_b",
            "show_action_a",
            "show_action_b",
        ]

        copied_count = 0
        for src_slot in src_slots:
            # Use rigify_action_slots.add() to add a new slot item
            tgt_slot = tgt_slots.add()
            
            for attr in slot_attributes:
                try:
                    if hasattr(src_slot, attr):
                        val = getattr(src_slot, attr)
                        setattr(tgt_slot, attr, val)
                except Exception as e:
                    # Some attributes might be read-only or fail depending on Blender/Rigify version
                    print(f"Skipped attribute '{attr}' on slot '{src_slot.name}': {e}")
            
            copied_count += 1

        self.report({'INFO'}, f"Successfully transferred {copied_count} action slot(s) from '{source_obj.name}' to '{target_obj.name}'.")
        return {'FINISHED'}


class VIEW3D_PT_rigify_action_slots_transfer(bpy.types.Panel):
    """Creates a panel in the 3D Viewport sidebar to easily run the transfer tool"""
    bl_label = "Rigify Action Slots Transfer"
    bl_idname = "VIEW3D_PT_rigify_action_slots_transfer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rigging"

    def draw(self, context):
        layout = self.layout
        
        scene = context.scene
        active = context.active_object
        
        layout.operator("armature.transfer_rigify_action_slots", text="Transfer Action Slots")
        
        # Helpful guidance text in UI
        box = layout.box()
        box.label(text="Instructions:", icon='INFO')
        box.label(text="1. Select the SOURCE armature first.")
        box.label(text="2. Shift-select the TARGET armature last (active).")


classes = (
    ARMATURE_OT_transfer_rigify_action_slots,
    VIEW3D_PT_rigify_action_slots_transfer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()