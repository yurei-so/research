package so.yurei.voxelguidance;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.PosixFilePermission;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

final class LaunchRecipeManager {
    private static final Pattern ID = Pattern.compile("[a-z0-9][a-z0-9._-]{0,63}");
    private static final Set<String> PRESETS = Set.of("empty", "construction-kit-v1", "recovery-kit-v1");
    private Pending pending;
    private Path attemptedWorld;

    void tick(Minecraft client, SessionRecorder recorder) {
        if (client.player == null || client.level == null || client.getSingleplayerServer() == null || recorder.active()) return;
        try {
            if (pending == null) discover(client);
            if (pending == null) return;
            pending.ticks++;
            if (pending.ticks < 20 || !inventoryMatches(client, pending.recipe.preset)) return;
            recorder.start(client, pending.recipe.taskId, pending.recipe.protocolId);
            client.player.displayClientMessage(Component.literal("[Voxel Guidance] Objective: " + pending.recipe.objective), false);
            pending = null;
        } catch (Exception error) {
            SessionRecorder.notify(client, "launch recipe failed: " + error.getMessage());
            pending = null;
        }
    }

    private void discover(Minecraft client) throws IOException {
        MinecraftServer server = client.getSingleplayerServer();
        if (server == null) return;
        Path world = server.getWorldPath(LevelResource.ROOT).toRealPath();
        if (world.equals(attemptedWorld)) return;
        attemptedWorld = world;
        Path game = OwnershipGate.requireOwnedGameDirectory();
        if (!world.getParent().equals(game.resolve("saves").toRealPath())) throw new IOException("world is outside managed saves");
        Path recipePath = world.resolve(".voxel-guidance-launch.json");
        if (!Files.isRegularFile(recipePath) || Files.isSymbolicLink(recipePath)) return;
        try {
            Set<PosixFilePermission> permissions = Files.getPosixFilePermissions(recipePath);
            if (!permissions.equals(Set.of(PosixFilePermission.OWNER_READ, PosixFilePermission.OWNER_WRITE))) {
                throw new IOException("launch recipe permissions are not private");
            }
        } catch (UnsupportedOperationException ignored) {}
        JsonObject recipeJson = object(recipePath);
        JsonObject marker = object(world.resolve(".prism-toolkit-world.json"));
        Recipe recipe = validate(recipeJson, marker, world, game);
        Path consumed = world.resolve(".voxel-guidance-launch.consumed.json");
        Files.move(recipePath, consumed, StandardCopyOption.ATOMIC_MOVE);
        pending = new Pending(recipe);
        server.execute(() -> apply(server, client.player.getUUID(), recipe.preset));
        SessionRecorder.notify(client, "preparing " + recipe.taskId);
    }

    private static Recipe validate(JsonObject json, JsonObject marker, Path world, Path game) throws IOException {
        if (!"voxel-guidance.launch-recipe".equals(string(json, "format")) || integer(json, "version") != 1
                || !OwnershipGate.INSTANCE_ID.equals(string(json, "instanceId"))
                || !world.getFileName().toString().equals(string(json, "worldId"))) throw new IOException("launch recipe identity mismatch");
        String task = string(json, "taskId"), protocol = string(json, "protocolId"), preset = string(json, "inventoryPreset");
        String objective = string(json, "objective"), markerId = string(json, "worldMarkerId");
        if (!ID.matcher(task).matches() || !ID.matcher(protocol).matches() || !PRESETS.contains(preset)
                || objective.isBlank() || objective.length() > 500 || objective.indexOf('\0') >= 0) throw new IOException("invalid launch recipe");
        if (!"prism-toolkit.world".equals(string(marker, "format")) || !markerId.equals(string(marker, "markerId"))
                || !world.getFileName().toString().equals(string(marker, "worldId"))) throw new IOException("world marker mismatch");
        Path root = game.getParent().getParent().getParent();
        JsonObject registry = object(root.resolve(".prism-toolkit/registry.json"));
        JsonObject worlds = registry.getAsJsonObject("worlds");
        JsonObject instance = worlds == null ? null : worlds.getAsJsonObject(OwnershipGate.INSTANCE_ID);
        JsonObject entry = instance == null ? null : instance.getAsJsonObject(world.getFileName().toString());
        if (entry == null || !markerId.equals(string(entry, "markerId"))) throw new IOException("world registry mismatch");
        return new Recipe(task, protocol, preset, objective);
    }

    private static void apply(MinecraftServer server, java.util.UUID playerId, String preset) {
        ServerPlayer player = server.getPlayerList().getPlayer(playerId);
        if (player == null) return;
        var source = player.createCommandSourceStack().withPermission(4).withSuppressedOutput();
        server.getCommands().performPrefixedCommand(source, "clear");
        if (!preset.equals("empty")) {
            for (String command : new String[]{"give @s minecraft:oak_planks 64", "give @s minecraft:cobblestone 32",
                    "give @s minecraft:glass 16", "give @s minecraft:torch 16", "give @s minecraft:oak_door 1",
                    "give @s minecraft:stone_pickaxe 1", "give @s minecraft:stone_axe 1", "give @s minecraft:bread 8"}) {
                server.getCommands().performPrefixedCommand(source, command);
            }
        }
        server.getCommands().performPrefixedCommand(source, "time set day");
        server.getCommands().performPrefixedCommand(source, "weather clear");
        server.getCommands().performPrefixedCommand(source, "gamemode survival");
    }

    private static boolean inventoryMatches(Minecraft client, String preset) {
        if (client.player == null) return false;
        Map<String, Integer> expected = preset.equals("empty") ? Map.of() : Map.of(
                "minecraft:oak_planks", 64, "minecraft:cobblestone", 32, "minecraft:glass", 16,
                "minecraft:torch", 16, "minecraft:oak_door", 1, "minecraft:stone_pickaxe", 1,
                "minecraft:stone_axe", 1, "minecraft:bread", 8);
        java.util.Map<String, Integer> actual = new java.util.HashMap<>();
        for (int slot = 0; slot < client.player.getInventory().getContainerSize(); slot++) {
            ItemStack stack = client.player.getInventory().getItem(slot);
            if (!stack.isEmpty()) actual.merge(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(), stack.getCount(), Integer::sum);
        }
        return actual.equals(expected);
    }

    private static JsonObject object(Path path) throws IOException {
        try (var reader = Files.newBufferedReader(path)) { return JsonParser.parseReader(reader).getAsJsonObject(); }
        catch (RuntimeException error) { throw new IOException("invalid " + path.getFileName(), error); }
    }
    private static String string(JsonObject object, String key) throws IOException {
        if (object == null || !object.has(key) || !object.get(key).isJsonPrimitive()) throw new IOException("missing " + key);
        return object.get(key).getAsString();
    }
    private static int integer(JsonObject object, String key) throws IOException {
        try { return object.get(key).getAsInt(); } catch (RuntimeException error) { throw new IOException("missing " + key); }
    }
    private record Recipe(String taskId, String protocolId, String preset, String objective) {}
    private static final class Pending { final Recipe recipe; int ticks; Pending(Recipe recipe) { this.recipe = recipe; } }
}
