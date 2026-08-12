
import bpy
from bpy.types import Panel, UIList

class DATA_UL_bone_collections(UIList):
    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        bcoll = item
        # In Weight Paint mode, the active object is the mesh, so we find its armature.
        armature_obj = context.object.find_armature()
        if not armature_obj:
            return
        arm = armature_obj.data

        # Draw the collection name.
        layout.prop(bcoll, "name", text="", emboss=False, icon='DOT')

        # Draw library override icon if necessary.
        if arm.override_library:
            icon = 'LIBRARY_DATA_OVERRIDE' if bcoll.is_local_override else 'BLANK1'
            layout.prop(bcoll, "is_local_override", text="", emboss=False, icon=icon)

        # Draw the visibility toggle icon, which is crucial for weight painting.
        layout.prop(bcoll, "is_visible", text="", emboss=False, icon='HIDE_OFF' if bcoll.is_visible else 'HIDE_ON')
        layout.prop(bcoll, "is_solo", text="", emboss=False, icon='SOLO_ON' if bcoll.is_solo else 'SOLO_OFF')

class WEIGHTPAINT_PT_bone_collections(Panel):
    bl_label = "Bone Collections"
    bl_idname = "WEIGHTPAINT_PT_bone_collections"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Skinning'

    @classmethod
    def poll(cls, context):
        """
        Ensures the panel only shows up in Weight Paint mode when a mesh
        with a valid armature is selected.
        """
        if context.mode != 'PAINT_WEIGHT':
            return False
        mesh = context.active_object
        obj = context.selected_objects
        if len(obj) > 2:
            return False
        
        if not mesh or mesh.type != 'MESH':
            return False
        
        armature_obj = mesh.find_armature()
        if not armature_obj:
            return False
        
        if armature_obj not in context.selected_objects:
            return False
        
        return True

    def draw(self, context):
        """Draws the panel UI."""
        layout = self.layout
        obj = context.object
        armature_obj = obj.find_armature()
        
        if armature_obj and armature_obj.data:
            arm = armature_obj.data
            row = layout.row(align=True)
            row.prop(arm, "pose_position", expand=True)
            layout.separator()
            
            # Main row for the list and its basic controls
            row = layout.row()
            
            # Use template_list to draw the UIList defined above.
            row.template_list(
                "DATA_UL_bone_collections", 
                "bone_collections", 
                arm, 
                "collections", 
                arm.collections, 
                "active_index"
            )
            
            # Add the operator buttons for managing collections.
            col = row.column(align=True)
            col.operator("armature.collection_add", icon='ADD', text="")
            col.operator("armature.collection_remove", icon='REMOVE', text="")
            col.separator()
            col.menu("ARMATURE_MT_collection_context_menu", icon='DOWNARROW_HLT', text="")

            # Add rows for assigning/selecting bones (useful for setup).
            row = layout.row()
            sub = row.row(align=True)
            sub.operator("armature.collection_assign", text="Assign")
            sub.operator("armature.collection_unassign", text="Remove")

            sub = row.row(align=True)
            sub.operator("armature.collection_select", text="Select")
            sub.operator("armature.collection_deselect", text="Deselect")

# A list of all classes that need to be registered with Blender.
classes = (
    DATA_UL_bone_collections,
    WEIGHTPAINT_PT_bone_collections,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
