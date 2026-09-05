# Panel transfer baseline

Trains only the classifier head of an ImageNet-pretrained MobileNet V3 Small on
the four private development batches. It evaluates leave-one-batch-out and
never reads the spent or future frozen holdouts. The experiment has no live
capture or input-control capability.
