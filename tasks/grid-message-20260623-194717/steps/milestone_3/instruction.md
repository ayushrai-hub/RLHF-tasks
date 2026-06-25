This milestone integrates the first two milestones to receive a multi-bytes message terminated by a null character. You should read characters until a null character is found and return the message and the number of frames processed. You should stop receiving frames when you get the null character. You should keep track of the number of frames processed and print it out.

The following 3 lines are a snippet given to simplify the explanation. This is the exact format that the grader expects. Print the first line and whichever of the 2nd or 3rd line applies. Please use this code.

    - printf("FRAMES_PROCESSED: %d\n", frames_processed);
    - printf("DECODED: %s\n", decoded_message);
    - printf("NO message found\n");
