package so.yurei.voxelguidance;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.world.InteractionResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.argument;
import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.literal;

public final class VoxelGuidanceClient implements ClientModInitializer {
    private static final Logger LOGGER = LoggerFactory.getLogger("voxel-guidance-bridge");
    private final SessionRecorder recorder = new SessionRecorder();
    private final LaunchRecipeManager launchRecipes = new LaunchRecipeManager();

    @Override
    public void onInitializeClient() {
        LOGGER.info("Voxel Guidance Bridge initialized; recording is off");
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            launchRecipes.tick(client, recorder);
            recorder.tick(client);
        });
        ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> recorder.disconnect(client));
        AttackBlockCallback.EVENT.register((player, world, hand, position, direction) -> {
            recorder.watchBreak(world, position);
            return InteractionResult.PASS;
        });
        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            recorder.watchPlacement(player, world, hand, hit);
            return InteractionResult.PASS;
        });
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> dispatcher.register(
                literal("vg")
                    .then(literal("start")
                        .then(argument("task", StringArgumentType.word())
                            .then(argument("protocol", StringArgumentType.word())
                                .executes(context -> run(context.getSource().getClient(), () -> recorder.start(
                                        context.getSource().getClient(),
                                        StringArgumentType.getString(context, "task"),
                                        StringArgumentType.getString(context, "protocol")))))))
                    .then(literal("marker")
                        .then(argument("name", StringArgumentType.word())
                            .executes(context -> run(context.getSource().getClient(), () -> recorder.marker(
                                    context.getSource().getClient(), StringArgumentType.getString(context, "name"))))))
                    .then(literal("stop").executes(context -> run(context.getSource().getClient(),
                            () -> recorder.stop(context.getSource().getClient(), "explicit_stop"))))
                    .then(literal("status").executes(context -> {
                        SessionRecorder.notify(context.getSource().getClient(), recorder.active() ? "recording" : "idle");
                        return 1;
                    }))
        ));
    }

    private static int run(net.minecraft.client.Minecraft client, CheckedAction action) {
        try { action.run(); return 1; }
        catch (Exception error) { SessionRecorder.notify(client, error.getMessage()); return 0; }
    }

    @FunctionalInterface
    private interface CheckedAction { void run() throws Exception; }
}
