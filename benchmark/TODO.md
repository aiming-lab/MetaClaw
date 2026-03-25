1. 修改/home/xkaiwen/workspace/metaclaw-test/benchmark/scripts下的skills_only_run和rl_run中关于配置文件的处理，这两个文件的cfg里增加一条'original-skill-dir'，这个目录里有一些初始skill文件，在做config覆写之前，会先从'original-skill-dir'复制到一个以时间命名的临时目录，用作配置中的skills.dir，从而保证每次运行时初始的skill目录相同，然后覆写配置时重映射到临时skill目录，整个运行结束后删掉临时目录
2. 为metaclaw start增加功能，不再固定只能读取`~/.metaclaw/config.yaml`的配置，而是可以接受一个额外参数传入指定的yaml路径，而所有benchmark/scripts都从原先的覆写到默认配置路径，改成创建临时配置文件，用新版metaclaw start读取该配置，在全部运行结束后删除

注意，当前目录结构非常乱，要仔细查找代码，确保每一个相关地方都妥善修改