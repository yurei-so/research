package so.yurei.voxelguidance;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonElement;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
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
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

final class LaunchRecipeManager {
    private static final Pattern ID = Pattern.compile("[a-z0-9][a-z0-9._-]{0,63}");
    private static final Set<String> PRESETS = Set.of("empty", "construction-kit-v1", "recovery-kit-v1");
    private Pending pending;
    private Active active;
    private Path attemptedWorld;

    void tick(Minecraft client, SessionRecorder recorder) {
        if (client.player == null || client.level == null || client.getSingleplayerServer() == null) return;
        try {
            if (active != null) { automate(client, recorder); return; }
            if (recorder.active()) return;
            if (pending == null) discover(client);
            if (pending != null) {
                pending.ticks++;
                if (pending.ticks < 20 || !inventoryMatches(client, pending.recipe.preset)) return;
                recorder.start(client, pending.recipe.taskId, pending.recipe.protocolId);
                client.player.displayClientMessage(Component.literal("[Voxel Guidance] Objective: " + pending.recipe.objective), false);
                active = new Active(pending.recipe);
                pending = null;
            }
        } catch (Exception error) {
            SessionRecorder.notify(client, "launch recipe failed: " + error.getMessage());
            pending = null;
        }
    }

    private void automate(Minecraft client, SessionRecorder recorder) throws IOException {
        if (active == null || !recorder.active()) { active = null; return; }
        for (Rule rule : active.recipe.rules) {
            if (rule.fired || !matches(rule.trigger, client, recorder)) continue;
            rule.fired = true;
            if (rule.marker != null) recorder.marker(client, rule.marker);
            if ("kill_player".equals(rule.action)) {
                MinecraftServer server = client.getSingleplayerServer();
                if (server != null) server.execute(() -> command(server, client.player.getUUID(), "kill @s"));
            }
        }
        if (recorder.elapsedSeconds() < active.recipe.durationSeconds) return;
        String end = active.recipe.onDurationEnd;
        recorder.stop(client, "explicit_stop");
        active = null;
        if ("stop_and_exit_world".equals(end)) client.disconnect(new TitleScreen());
        else if ("stop_and_quit_game".equals(end)) client.stop();
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
        String objective = string(json, "objective"), markerId = string(json, "worldMarkerId"), recipeId = string(json, "recipeId");
        if (!ID.matcher(task).matches() || !ID.matcher(protocol).matches() || !PRESETS.contains(preset)
                || objective.isBlank() || objective.length() > 500 || objective.indexOf('\0') >= 0) throw new IOException("invalid launch recipe");
        if (!"prism-toolkit.world".equals(string(marker, "format")) || !markerId.equals(string(marker, "markerId"))
                || !world.getFileName().toString().equals(string(marker, "worldId"))) throw new IOException("world marker mismatch");
        Path root = game.getParent().getParent().getParent();
        JsonObject registry = object(root.resolve(".prism-toolkit/registry.json"));
        JsonObject worlds = registry.getAsJsonObject("worlds");
        JsonObject instance = worlds == null ? null : worlds.getAsJsonObject(OwnershipGate.INSTANCE_ID);
        JsonObject entry = instance == null ? null : instance.getAsJsonObject(world.getFileName().toString());
        if (entry == null || !markerId.equals(string(entry, "markerId"))
                || !recipeId.equals(string(entry, "launchRecipeId"))) throw new IOException("world registry mismatch");
        JsonObject automation = json.getAsJsonObject("automation");
        int duration = integer(automation, "durationSeconds");
        String onEnd = string(automation, "onDurationEnd");
        if (duration < 30 || duration > 3600 || !Set.of("stop_recording", "stop_and_exit_world", "stop_and_quit_game").contains(onEnd)) {
            throw new IOException("invalid automation duration or end action");
        }
        List<Rule> rules = new ArrayList<>();
        if (!automation.has("rules") || !automation.get("rules").isJsonArray() || automation.getAsJsonArray("rules").size() > 16) {
            throw new IOException("invalid automation rules");
        }
        for (JsonElement element : automation.getAsJsonArray("rules")) {
            JsonObject rule = element.getAsJsonObject();
            String ruleMarker = rule.has("marker") ? string(rule, "marker") : null;
            String action = rule.has("action") ? string(rule, "action") : null;
            if (ruleMarker == null && action == null) throw new IOException("automation rule has no effect");
            if (ruleMarker != null && !Set.of("plan_started", "plan_revised", "setback", "recovered", "task_complete").contains(ruleMarker)) throw new IOException("invalid automated marker");
            if (action != null && !"kill_player".equals(action)) throw new IOException("invalid automated action");
            rules.add(new Rule(ruleMarker, action, trigger(rule.getAsJsonObject("when"), 0)));
        }
        return new Recipe(task, protocol, preset, objective, duration, onEnd, rules);
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

    private static void command(MinecraftServer server, java.util.UUID playerId, String command) {
        ServerPlayer player = server.getPlayerList().getPlayer(playerId);
        if (player != null) server.getCommands().performPrefixedCommand(
                player.createCommandSourceStack().withPermission(4).withSuppressedOutput(), command);
    }

    private static Trigger trigger(JsonObject json, int depth) throws IOException {
        if (json == null || depth > 4) throw new IOException("invalid automation trigger");
        String type = string(json, "type");
        Trigger result = new Trigger(type);
        switch (type) {
            case "elapsed_seconds" -> result.number = integer(json, "seconds");
            case "inventory_contains" -> { result.item = string(json, "item"); result.number = integer(json, "count"); }
            case "near_spawn" -> result.radius = decimal(json, "radius");
            case "death_count", "respawn_count" -> result.number = integer(json, "count");
            case "block_action_count" -> { result.action = string(json, "action"); result.category = string(json, "category"); result.number = integer(json, "count"); }
            case "all", "any" -> {
                if (!json.has("triggers") || !json.get("triggers").isJsonArray() || json.getAsJsonArray("triggers").isEmpty()
                        || json.getAsJsonArray("triggers").size() > 8) throw new IOException("invalid compound trigger");
                for (JsonElement child : json.getAsJsonArray("triggers")) result.children.add(trigger(child.getAsJsonObject(), depth + 1));
            }
            default -> throw new IOException("unknown automation trigger");
        }
        if ((type.equals("elapsed_seconds") && (result.number < 0 || result.number > 3600))
                || (type.equals("inventory_contains") && (result.number < 1 || result.number > 65536
                    || !result.item.matches("[a-z0-9_.-]+:[a-z0-9_./-]+")))
                || (type.equals("near_spawn") && (!Double.isFinite(result.radius) || result.radius < 0 || result.radius > 1024))
                || ((type.equals("death_count") || type.equals("respawn_count")) && (result.number < 1 || result.number > 100))
                || (type.equals("block_action_count") && (result.number < 1 || result.number > 100000
                    || !Set.of("placed", "broken").contains(result.action)
                    || !Set.of("building", "resource", "functional", "other").contains(result.category)))) {
            throw new IOException("automation trigger outside bounds");
        }
        return result;
    }

    private static boolean matches(Trigger trigger, Minecraft client, SessionRecorder recorder) {
        return switch (trigger.type) {
            case "elapsed_seconds" -> recorder.elapsedSeconds() >= trigger.number;
            case "inventory_contains" -> itemCount(client, trigger.item) >= trigger.number;
            case "near_spawn" -> {
                var spawn = client.level.getSharedSpawnPos();
                double dx = client.player.getX() - (spawn.getX() + 0.5), dz = client.player.getZ() - (spawn.getZ() + 0.5);
                yield dx * dx + dz * dz <= trigger.radius * trigger.radius;
            }
            case "death_count" -> recorder.deathCount() >= trigger.number;
            case "respawn_count" -> recorder.respawnCount() >= trigger.number;
            case "block_action_count" -> recorder.blockActionCount(trigger.action, trigger.category) >= trigger.number;
            case "all" -> trigger.children.stream().allMatch(child -> matches(child, client, recorder));
            case "any" -> trigger.children.stream().anyMatch(child -> matches(child, client, recorder));
            default -> false;
        };
    }

    private static int itemCount(Minecraft client, String item) {
        int count = 0;
        for (int slot = 0; slot < client.player.getInventory().getContainerSize(); slot++) {
            ItemStack stack = client.player.getInventory().getItem(slot);
            if (!stack.isEmpty() && BuiltInRegistries.ITEM.getKey(stack.getItem()).toString().equals(item)) count += stack.getCount();
        }
        return count;
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
    private static double decimal(JsonObject object, String key) throws IOException {
        try { return object.get(key).getAsDouble(); } catch (RuntimeException error) { throw new IOException("missing " + key); }
    }
    private record Recipe(String taskId, String protocolId, String preset, String objective,
                          int durationSeconds, String onDurationEnd, List<Rule> rules) {}
    private static final class Rule { final String marker, action; final Trigger trigger; boolean fired;
        Rule(String marker, String action, Trigger trigger) { this.marker = marker; this.action = action; this.trigger = trigger; } }
    private static final class Trigger { final String type; int number; double radius; String item, action, category;
        final List<Trigger> children = new ArrayList<>(); Trigger(String type) { this.type = type; } }
    private static final class Active { final Recipe recipe; Active(Recipe recipe) { this.recipe = recipe; } }
    private static final class Pending { final Recipe recipe; int ticks; Pending(Recipe recipe) { this.recipe = recipe; } }
}
