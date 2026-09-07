package so.yurei.voxelguidance;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.BlockHitResult;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Instant;
import java.time.Duration;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.regex.Pattern;

final class SessionRecorder {
    private static final Gson GSON = new Gson();
    private static final Pattern ID = Pattern.compile("[a-z0-9][a-z0-9._-]{0,63}");
    private static final Set<String> MARKERS = Set.of(
            "plan_started", "plan_revised", "setback", "recovered", "task_complete");
    private BufferedWriter writer;
    private String sessionId;
    private String taskId;
    private int sequence;
    private int ticks;
    private Instant startedAt;
    private Map<String, Integer> inventory = Map.of();
    private float previousHealth;
    private boolean previousDead;
    private final Map<BlockPos, PendingBlock> pendingBlocks = new HashMap<>();

    synchronized void start(Minecraft client, String task, String protocol) throws IOException {
        if (writer != null) throw new IOException("a recording is already active");
        if (!ID.matcher(task).matches() || !ID.matcher(protocol).matches()) {
            throw new IOException("task and protocol IDs must use lowercase letters, digits, dot, dash, or underscore");
        }
        if (client.player == null || client.level == null) throw new IOException("enter a world before recording");
        Path game = OwnershipGate.requireOwnedGameDirectory();
        Path directory = game.resolve(".voxel-guidance/private/sessions");
        Files.createDirectories(directory);
        try { Files.setPosixFilePermissions(directory, PosixFilePermissions.fromString("rwx------")); }
        catch (UnsupportedOperationException ignored) {}
        sessionId = UUID.randomUUID().toString();
        taskId = task;
        sequence = 0;
        ticks = 0;
        startedAt = Instant.now();
        inventory = inventorySnapshot(client.player);
        previousHealth = client.player.getHealth();
        previousDead = client.player.isDeadOrDying();
        pendingBlocks.clear();
        Path output = directory.resolve(sessionId + ".ndjson");
        writer = Files.newBufferedWriter(output, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        try { Files.setPosixFilePermissions(output, PosixFilePermissions.fromString("rw-------")); }
        catch (UnsupportedOperationException ignored) {}
        write("session_start", payload("protocol_id", protocol));
        notify(client, "recording " + task);
    }

    synchronized void marker(Minecraft client, String marker) throws IOException {
        requireActive();
        if (!MARKERS.contains(marker)) throw new IOException("unknown marker");
        write("marker", payload("marker", marker));
        notify(client, "marked " + marker);
    }

    synchronized void stop(Minecraft client, String reason) throws IOException {
        requireActive();
        try {
            if (client.level != null) checkPendingBlocks(client.level);
            if (client.player != null) {
                sampleHealth(client.player);
                sampleInventory(client.player);
            }
            write("session_end", payload("reason", reason));
        }
        finally { writer.close(); writer = null; }
        notify(client, "recording stopped");
    }

    synchronized void tick(Minecraft client) {
        if (writer == null || client.player == null || client.level == null) return;
        ticks++;
        try {
            checkPendingBlocks(client.level);
            sampleHealth(client.player);
        } catch (IOException error) {
            fail(client, error);
            return;
        }
        if (ticks % 20 != 0) return;
        try {
            String dimension = switch (client.level.dimension().location().getPath()) {
                case "the_nether" -> "nether";
                case "the_end" -> "end";
                default -> "overworld";
            };
            JsonObject payload = new JsonObject();
            payload.addProperty("x", client.player.getX());
            payload.addProperty("y", client.player.getY());
            payload.addProperty("z", client.player.getZ());
            payload.addProperty("dimension", dimension);
            write("position_sample", payload);
            sampleInventory(client.player);
            long elapsed = Duration.between(startedAt, Instant.now()).toSeconds();
            notify(client, "RECORDING " + taskId + " " + (elapsed / 60) + ":" + String.format("%02d", elapsed % 60));
        } catch (IOException error) {
            fail(client, error);
        }
    }

    synchronized void disconnect(Minecraft client) {
        if (writer == null) return;
        try { stop(client, "disconnected"); }
        catch (IOException error) { fail(client, error); }
    }

    synchronized boolean active() { return writer != null; }

    synchronized void watchBreak(Level world, BlockPos position) {
        if (writer == null || !world.isClientSide()) return;
        Block original = world.getBlockState(position).getBlock();
        if (!world.getBlockState(position).isAir()) {
            pendingBlocks.put(position.immutable(), new PendingBlock(position.immutable(), original, null,
                    blockCategory(original), dimension(world), ticks + 200));
        }
    }

    synchronized void watchPlacement(Player player, Level world, InteractionHand hand, BlockHitResult hit) {
        if (writer == null || !world.isClientSide()) return;
        ItemStack stack = player.getItemInHand(hand);
        if (!(stack.getItem() instanceof BlockItem blockItem)) return;
        BlockPos position = world.getBlockState(hit.getBlockPos()).canBeReplaced()
                ? hit.getBlockPos() : hit.getBlockPos().relative(hit.getDirection());
        Block original = world.getBlockState(position).getBlock();
        pendingBlocks.put(position.immutable(), new PendingBlock(position.immutable(), original, blockItem.getBlock(),
                blockCategory(blockItem.getBlock()), dimension(world), ticks + 40));
    }

    private void requireActive() throws IOException {
        if (writer == null) throw new IOException("no recording is active");
    }

    private void sampleInventory(Player player) throws IOException {
        Map<String, Integer> current = inventorySnapshot(player);
        Set<String> categories = new HashSet<>(inventory.keySet());
        categories.addAll(current.keySet());
        for (String category : categories) {
            int delta = current.getOrDefault(category, 0) - inventory.getOrDefault(category, 0);
            if (delta != 0) {
                JsonObject payload = new JsonObject();
                payload.addProperty("category", category);
                payload.addProperty("delta", delta);
                write("inventory_delta", payload);
            }
        }
        inventory = current;
    }

    private void sampleHealth(Player player) throws IOException {
        float health = player.getHealth();
        boolean dead = player.isDeadOrDying();
        if (!previousDead && health < previousHealth) {
            JsonObject payload = new JsonObject();
            payload.addProperty("amount", previousHealth - health);
            payload.addProperty("source_category", "other");
            write("damage", payload);
        }
        if (!previousDead && dead) write("death", new JsonObject());
        else if (previousDead && !dead) write("respawn", new JsonObject());
        previousHealth = health;
        previousDead = dead;
    }

    private void checkPendingBlocks(Level world) throws IOException {
        String currentDimension = dimension(world);
        Iterator<PendingBlock> iterator = pendingBlocks.values().iterator();
        while (iterator.hasNext()) {
            PendingBlock pending = iterator.next();
            if (ticks > pending.expiresAt()) { iterator.remove(); continue; }
            if (!pending.dimension().equals(currentDimension)) continue;
            Block current = world.getBlockState(pending.position()).getBlock();
            boolean confirmed = pending.expected() != null
                    ? current == pending.expected() && current != pending.original()
                    : current != pending.original();
            if (confirmed) {
                JsonObject payload = new JsonObject();
                payload.addProperty("action", pending.expected() == null ? "broken" : "placed");
                payload.addProperty("category", pending.category());
                payload.addProperty("count", 1);
                write("block_action", payload);
                iterator.remove();
            }
        }
    }

    private static Map<String, Integer> inventorySnapshot(Player player) {
        Map<String, Integer> result = new HashMap<>();
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++) {
            ItemStack stack = player.getInventory().getItem(slot);
            if (!stack.isEmpty()) result.merge(itemCategory(stack), stack.getCount(), Integer::sum);
        }
        return result;
    }

    private static String itemCategory(ItemStack stack) {
        String path = BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath();
        if (contains(path, "ore", "ingot", "raw_", "diamond", "emerald", "coal", "redstone", "lapis", "quartz")) return "resource";
        if (contains(path, "pickaxe", "axe", "shovel", "hoe", "sword", "shears", "fishing_rod", "bow")) return "tool";
        if (contains(path, "bread", "apple", "carrot", "potato", "beef", "pork", "chicken", "mutton", "fish", "berry", "stew")) return "food";
        if (stack.getItem() instanceof BlockItem) return "building";
        return "other";
    }

    private static String blockCategory(Block block) {
        String path = BuiltInRegistries.BLOCK.getKey(block).getPath();
        if (contains(path, "ore", "ancient_debris")) return "resource";
        if (contains(path, "chest", "furnace", "crafting_table", "barrel", "door", "bed", "anvil")) return "functional";
        if (contains(path, "planks", "brick", "stone", "glass", "concrete", "terracotta", "log", "wood")) return "building";
        return "other";
    }

    private static boolean contains(String value, String... needles) {
        return Arrays.stream(needles).anyMatch(value::contains);
    }

    private static String dimension(Level world) {
        return world.dimension().location().toString();
    }

    private void write(String kind, JsonObject payload) throws IOException {
        JsonObject event = new JsonObject();
        event.addProperty("format", "voxel-guidance.event");
        event.addProperty("version", 1);
        event.addProperty("session_id", sessionId);
        event.addProperty("sequence", sequence++);
        event.addProperty("observed_at", Instant.now().truncatedTo(ChronoUnit.MILLIS).toString());
        event.addProperty("instance_id", OwnershipGate.INSTANCE_ID);
        event.addProperty("task_id", taskId);
        event.addProperty("kind", kind);
        event.add("payload", payload);
        writer.write(GSON.toJson(event));
        writer.newLine();
        writer.flush();
    }

    private static JsonObject payload(String key, String value) {
        JsonObject payload = new JsonObject();
        payload.addProperty(key, value);
        return payload;
    }

    private void fail(Minecraft client, IOException error) {
        try { if (writer != null) writer.close(); } catch (IOException ignored) {}
        writer = null;
        notify(client, "recording failed: " + error.getMessage());
    }

    private record PendingBlock(BlockPos position, Block original, Block expected, String category,
                                String dimension, int expiresAt) {}

    static void notify(Minecraft client, String message) {
        if (client.player != null) client.player.displayClientMessage(Component.literal("[Voxel Guidance] " + message), true);
    }
}
