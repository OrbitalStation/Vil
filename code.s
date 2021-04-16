	.file    "/home/rtarasenko/JetBrains/PyCharmProjects/VikaLang/code.s"
	.code64
	.text

	.globl   main
	.type    main, @function
main:
	pushq %rbp
	movq  %rsp, %rbp
	subq  $7, %rbp

	xorw  %ax, %ax
	movb  7(%rbp), %al
	addw  6(%rbp), %ax
	movl  %eax, 4(%rbp)

.LE0:
	addq  $7, %rbp
	popq  %rbp
	retq

	.size    main, . - main
