bl_info = {
    "name": "Animation Tools Vizor",
    "author": "Mikhail Lebedev",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Animation Tab",
    "description": "Animation tools",
    "category": "Animation",
}

import importlib

module_names = ("tools.animation.animation_mirror",
           "tools.animation.animation_tab",
           "tools.animation.bake_action",
           "tools.animation.blender_add_on_bone_primitive_placer",
           "tools.animation.clean_curves_markers",
           "tools.animation.mask_selected_geometry",
           "tools.animation.offset_action_animation",
           "tools.animation.update_cursor_location",
           "tools.animation.search_and_replace_fcurve_data",
           "tools.animation.wiggle_2",
           "tools.fbx.asset_action",
           "tools.fbx.export_actions_fbx",
           "tools.render.render_animation_sequences",
           "tools.render.render_gif",
           "tools.skining.bone_layers",
           "tools.skining.transfer_vertex_order",)

is_reloading = 'bpy' in locals()
modules = []

for module_name in module_names:
    mod = importlib.import_module(f".{module_name}", package=__package__)

    if is_reloading:
        importlib.reload(mod)

    modules.append(mod)

import bpy

def register():
    for module in modules:
        if hasattr(module, "register"):
            module.register()
            
def unregister():
    for module in reversed(modules):
        if hasattr(module, "unregister"):
            module.unregister()


if __name__ == "__main__":
    register()
